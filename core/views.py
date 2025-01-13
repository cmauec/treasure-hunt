"""
Views for the core app.
"""

import json
from datetime import datetime

import pytz
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic.edit import CreateView

from .forms import CustomUserCreationForm
from .models import Clue, TreasureHunt, UserProgress
from .utils import generate_image_embedding


def login_view(request):
    """
    View function for handling user login
    """
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get("next", "treasure_hunt_list")
                return redirect(next_url)
    else:
        form = AuthenticationForm()

    # Añadir clases de Bootstrap a los campos del formulario
    form.fields["username"].widget.attrs.update(
        {"class": "form-control", "placeholder": "Enter your username"}
    )
    form.fields["password"].widget.attrs.update(
        {"class": "form-control", "placeholder": "Enter your password"}
    )

    return render(request, "core/login.html", {"form": form})


class SignUpView(CreateView):
    """
    View function for signing up a new user.
    """

    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "core/signup.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Account created successfully. Please log in")
        return response


def logout_view(request):
    """
    Custom logout view that logs out the user, clears messages and redirects to login page
    """
    storage = messages.get_messages(request)
    for _ in storage:
        # Iterating through messages marks them as used
        pass
    storage.used = True

    logout(request)
    return redirect("login")


@login_required
def treasure_hunt_list(request):
    """
    View function for displaying the list of treasure hunts.

    Shows all public treasure hunts and private hunts created by the current user.
    For each hunt, displays progress information including completion status,
    points earned, and percentage completed.

    Args:
        request: The HTTP request object

    Returns:
        Rendered template with list of treasure hunts and their associated progress data
    """
    treasure_hunts = TreasureHunt.objects.all()
    treasure_hunts = treasure_hunts.filter(is_public=True) | treasure_hunts.filter(
        creator=request.user
    )

    user_progress = {
        progress.treasure_hunt_id: {
            "is_completed": progress.is_completed,
            "total_points": progress.total_points,
            "current_clue_order": (
                progress.current_clue.order if progress.current_clue else 0
            ),
            "total_clues": progress.treasure_hunt.clues.count(),
        }
        for progress in UserProgress.objects.filter(user=request.user).select_related(
            "current_clue", "treasure_hunt"
        )
    }

    hunts_data = []
    for hunt in treasure_hunts:
        progress_data = user_progress.get(
            hunt.id,
            {
                "is_completed": False,
                "total_points": 0,
                "current_clue_order": 0,
                "total_clues": hunt.clues.count(),
            },
        )

        # Calculate the progress percentage
        progress_percentage = (
            (
                progress_data["total_points"]
                / (progress_data["total_clues"] * hunt.points_per_clue)
            )
            * 100
            if progress_data["total_clues"] > 0
            else 0
        )
        if progress_data["is_completed"]:
            progress_percentage = 100
        elif progress_data["total_clues"] > 0:
            # Subtract 1 from current_clue_order because the order starts at 1
            current = max(0, progress_data["current_clue_order"] - 1)
            progress_percentage = (current / progress_data["total_clues"]) * 100
        else:
            progress_percentage = 0

        # Check if hunt has expired
        is_expired = hunt.end_date and hunt.end_date < timezone.now()

        hunts_data.append(
            {
                "hunt": hunt,
                "is_completed": progress_data["is_completed"],
                "total_points": progress_data["total_points"],
                "progress_percentage": progress_percentage,
                "is_expired": is_expired,
            }
        )

    context = {
        "treasure_hunts": hunts_data,
        "user": request.user,
    }
    return render(request, "core/treasure_hunt_list.html", context)


@login_required
def view_hunt(request, hunt_id):
    """
    View function for displaying a treasure hunt.
    """
    treasure_hunt = get_object_or_404(TreasureHunt, pk=hunt_id)

    # Check if the hunt has expired
    if treasure_hunt.end_date and treasure_hunt.end_date < timezone.now():
        messages.error(
            request, "This treasure hunt has ended and is no longer available"
        )
        return redirect("hunt_details", hunt_id=hunt_id)

    # Prevent creators from playing their own hunts
    if treasure_hunt.creator == request.user:
        messages.error(
            request, "You cannot play a treasure hunt that you have created yourself"
        )
        return redirect("hunt_details", hunt_id=hunt_id)

    # Check if user is inscribed
    user_progress = UserProgress.objects.filter(
        user=request.user, treasure_hunt=treasure_hunt
    ).first()

    if not user_progress:
        messages.error(request, "You must enroll in the hunt before you can start it.")
        return redirect("hunt_details", hunt_id=hunt_id)

    context = {
        "treasure_hunt": treasure_hunt,
        "progress": user_progress,
        "current_clue": user_progress.current_clue,
    }
    return render(request, "core/view_hunt.html", context)


@login_required
def verify_location(request, hunt_id):
    """
    View function for verifying the user's location against a treasure hunt's clues.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_lat = float(data.get("latitude"))
        user_lng = float(data.get("longitude"))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid location data"}, status=400)

    # Get the user's progress
    progress = get_object_or_404(
        UserProgress, user=request.user, treasure_hunt_id=hunt_id
    )
    current_clue = progress.current_clue

    # Verify if the coordinates match (with a margin of error of 10 meters)
    margin = 0.0001  # Approximately 10 meters
    if (
        abs(current_clue.latitude - user_lat) <= margin
        and abs(current_clue.longitude - user_lng) <= margin
    ):
        # Get the next clue
        next_clue = progress.treasure_hunt.clues.filter(
            order__gt=current_clue.order
        ).first()

        # Award points for completing the current clue
        progress.total_points += progress.treasure_hunt.points_per_clue

        if next_clue:
            # Update the user to the next clue
            progress.current_clue = next_clue
            progress.save()
            return JsonResponse(
                {
                    "success": True,
                    "message": current_clue.unlock_message,
                    "next_clue": True,
                }
            )
        else:
            # This was the last clue - mark as completed
            progress.is_completed = True
            progress.completed_at = timezone.now()
            progress.total_points += progress.treasure_hunt.completion_points
            progress.save()
            return JsonResponse(
                {
                    "success": True,
                    "message": current_clue.unlock_message,
                    "completed": True,
                    "completion_url": reverse("hunt_completion", args=[hunt_id]),
                }
            )

    return JsonResponse(
        {
            "success": False,
            "message": "You're not close enough to the clue location. Keep searching!",
        }
    )


@login_required
def create_hunt(request):
    """
    View function for creating a treasure hunt.
    """
    if not request.user.has_perm("core.can_create_hunts"):
        messages.error(request, "You do not have permission to create treasure hunts")
        return redirect("treasure_hunt_list")

    if request.method == "POST":
        end_date_str = request.POST.get("end_date")
        user_timezone = request.POST.get("timezone", "UTC")
        if end_date_str:
            # Parse the datetime string
            local_datetime = datetime.strptime(end_date_str, "%Y-%m-%dT%H:%M")

            # Get the user's timezone
            try:
                user_tz = pytz.timezone(user_timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                user_tz = pytz.UTC

            # Localize the datetime to user's timezone
            local_datetime = user_tz.localize(local_datetime)

            # Convert to UTC
            utc_datetime = local_datetime.astimezone(pytz.UTC)

            # Remove timezone info if your model field is not timezone-aware
            end_date = utc_datetime.replace(tzinfo=None)
        else:
            end_date = None
        try:
            # Create the treasure hunt
            hunt = TreasureHunt.objects.create(
                title=request.POST.get("title"),
                description=request.POST.get("description"),
                creator=request.user,
                is_public=request.POST.get("is_public") == "on",
                points_per_clue=int(request.POST.get("points_per_clue", 10)),
                completion_points=int(request.POST.get("completion_points", 50)),
                completion_message=request.POST.get(
                    "completion_message",
                    "Congratulations! You have completed the treasure hunt.",
                ),
                end_date=end_date,
            )

            # Handle main image upload
            main_image = request.FILES.get("image")
            if main_image:
                hunt.image = main_image
                hunt.save()

            # Process clues
            clue_count = 0
            while True:
                hint_text = request.POST.get(f"clues[{clue_count}][hint_text]")
                if hint_text is None:
                    break

                clue = Clue.objects.create(
                    treasure_hunt=hunt,
                    hint_text=hint_text,
                    unlock_message=request.POST.get(
                        f"clues[{clue_count}][unlock_message]"
                    ),
                    latitude=float(request.POST.get(f"clues[{clue_count}][latitude]")),
                    longitude=float(
                        request.POST.get(f"clues[{clue_count}][longitude]")
                    ),
                    order=clue_count + 1,
                )

                # Handle image upload
                reference_image = request.FILES.get(
                    f"clues[{clue_count}][reference_image]"
                )
                if reference_image:
                    clue.reference_image = reference_image
                    image_embedding = generate_image_embedding(reference_image)
                    clue.image_embedding = image_embedding
                    clue.save()

                clue_count += 1

            return JsonResponse(
                {
                    "success": True,
                    "redirect_url": reverse(
                        "hunt_details", kwargs={"hunt_id": hunt.id}
                    ),
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return render(request, "core/create_hunt.html")


@login_required
def delete_hunt(request, hunt_id):
    """
    View function for deleting a treasure hunt.
    """
    hunt = get_object_or_404(TreasureHunt, pk=hunt_id)

    if hunt.creator != request.user:
        messages.error(request, "You do not have permission to delete this hunt")
        return redirect("treasure_hunt_list")

    if request.method == "POST":
        title = hunt.title
        hunt.delete()
        messages.success(request, f'The treasure hunt "{title}" has been deleted')
        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)


@login_required
def edit_hunt(request, hunt_id):
    """
    View function for editing a treasure hunt.
    """
    hunt = get_object_or_404(TreasureHunt, pk=hunt_id)

    if hunt.creator != request.user:
        messages.error(request, "You do not have permission to edit this hunt")
        return redirect("treasure_hunt_list")

    if request.method == "POST":
        end_date_str = request.POST.get("end_date")
        user_timezone = request.POST.get("timezone", "UTC")
        if end_date_str:
            # Parse the datetime string
            local_datetime = datetime.strptime(end_date_str, "%Y-%m-%dT%H:%M")

            # Get the user's timezone
            try:
                user_tz = pytz.timezone(user_timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                user_tz = pytz.UTC

            # Localize the datetime to user's timezone
            local_datetime = user_tz.localize(local_datetime)

            # Convert to UTC
            utc_datetime = local_datetime.astimezone(pytz.UTC)

            # Remove timezone info if your model field is not timezone-aware
            end_date = utc_datetime.replace(tzinfo=None)
        else:
            end_date = None
        try:
            hunt.title = request.POST.get("title")
            hunt.description = request.POST.get("description")
            hunt.is_public = request.POST.get("is_public") == "on"
            hunt.end_date = end_date
            hunt.completion_message = request.POST.get(
                "completion_message", hunt.completion_message
            )

            remove_image = request.POST.get("remove_image")
            main_image = request.FILES.get("image")

            if remove_image == "on" and hunt.image:
                hunt.image.delete()
                hunt.image = None
            elif main_image:
                hunt.image = main_image

            hunt.save()

            # Get existing clues to track which ones to delete
            existing_clues = {str(clue.id): clue for clue in hunt.clues.all()}
            processed_clue_ids = set()

            # Process clues
            clue_count = 0
            while True:
                hint_text = request.POST.get(f"clues[{clue_count}][hint_text]")
                if hint_text is None:
                    break

                clue_id = request.POST.get(f"clues[{clue_count}][id]")

                if clue_id and clue_id in existing_clues:
                    clue = existing_clues[clue_id]
                    clue.hint_text = hint_text
                    clue.unlock_message = request.POST.get(
                        f"clues[{clue_count}][unlock_message]"
                    )
                    clue.latitude = float(
                        request.POST.get(f"clues[{clue_count}][latitude]")
                    )
                    clue.longitude = float(
                        request.POST.get(f"clues[{clue_count}][longitude]")
                    )
                    clue.order = clue_count + 1
                    processed_clue_ids.add(clue_id)
                else:
                    # Create new clue
                    clue = Clue.objects.create(
                        treasure_hunt=hunt,
                        hint_text=hint_text,
                        unlock_message=request.POST.get(
                            f"clues[{clue_count}][unlock_message]"
                        ),
                        latitude=float(
                            request.POST.get(f"clues[{clue_count}][latitude]")
                        ),
                        longitude=float(
                            request.POST.get(f"clues[{clue_count}][longitude]")
                        ),
                        order=clue_count + 1,
                    )

                # Handle image upload or removal
                remove_image = request.POST.get(f"clues[{clue_count}][remove_image]")
                reference_image = request.FILES.get(
                    f"clues[{clue_count}][reference_image]"
                )

                if remove_image == "on" and clue.reference_image:
                    # Delete the existing image from Google Cloud Storage
                    try:
                        default_storage.delete(clue.reference_image.name)
                        print(f"Imagen borrada: {clue.reference_image.name}")
                    except Exception as e:
                        print(f"Error al borrar la imagen: {e}")
                    clue.reference_image = None
                    clue.image_embedding = None
                elif reference_image:
                    # If a new image is uploaded, it automatically replaces the existing one using Django's FileField
                    clue.reference_image = reference_image
                    image_embedding = generate_image_embedding(reference_image)
                    clue.image_embedding = image_embedding

                clue.save()
                clue_count += 1

            # Delete clues that were not processed
            clues_to_delete = set(existing_clues.keys()) - processed_clue_ids
            # Before deleting the clues, also delete their associated images
            for clue_id_str in clues_to_delete:
                clue_to_delete = existing_clues[clue_id_str]
                if clue_to_delete.reference_image:
                    try:
                        default_storage.delete(clue_to_delete.reference_image.name)
                        print(
                            f"Image deleted when removing clue: {clue_to_delete.reference_image.name}"
                        )
                    except Exception as e:
                        print(f"Error deleting image while removing clue: {e}")
            hunt.clues.filter(id__in=clues_to_delete).delete()

            return JsonResponse(
                {
                    "success": True,
                    "redirect_url": reverse(
                        "hunt_details", kwargs={"hunt_id": hunt.id}
                    ),
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    # Prepare clues data for template
    clues_data = []
    for clue in hunt.clues.all().order_by("order"):
        clue_data = {
            "id": str(clue.id),  # Convert UUID to string
            "hint_text": clue.hint_text,
            "unlock_message": clue.unlock_message,
            "latitude": clue.latitude,
            "longitude": clue.longitude,
        }
        if clue.reference_image:
            clue_data["reference_image"] = clue.reference_image.url
        clues_data.append(clue_data)

    context = {"treasure_hunt": hunt, "clues_json": json.dumps(clues_data)}
    return render(request, "core/edit_hunt.html", context)


@login_required
def hunt_details(request, hunt_id):
    """
    View function for displaying the details of a treasure hunt before starting it.
    """
    treasure_hunt = get_object_or_404(TreasureHunt, pk=hunt_id)

    # Get user progress if it exists
    user_progress = UserProgress.objects.filter(
        user=request.user, treasure_hunt=treasure_hunt
    ).first()

    # Check if hunt has expired
    is_expired = treasure_hunt.end_date and treasure_hunt.end_date < timezone.now()

    # Count total clues
    total_clues = treasure_hunt.clues.count()

    # Calculate total possible points
    total_possible_points = (
        total_clues * treasure_hunt.points_per_clue
    ) + treasure_hunt.completion_points

    # Calculate progress percentage
    progress_percentage = 0
    if user_progress and total_clues > 0:
        if user_progress.is_completed:
            progress_percentage = 100
        elif user_progress.current_clue:
            # Subtract 1 from order since it starts at 1
            current = max(0, user_progress.current_clue.order - 1)
            progress_percentage = (current / total_clues) * 100

    context = {
        "treasure_hunt": treasure_hunt,
        "user_progress": user_progress,
        "is_expired": is_expired,
        "total_clues": total_clues,
        "total_possible_points": total_possible_points,
        "is_creator": treasure_hunt.creator == request.user,
        "progress_percentage": progress_percentage,
    }
    return render(request, "core/hunt_details.html", context)


@login_required
def inscribe_hunt(request, hunt_id):
    """
    View function for inscribing a user in a treasure hunt.
    """
    treasure_hunt = get_object_or_404(TreasureHunt, pk=hunt_id)

    # Check if the hunt has expired
    if treasure_hunt.end_date and treasure_hunt.end_date < timezone.now():
        messages.error(
            request, "This treasure hunt has expired and is no longer available"
        )
        return redirect("hunt_details", hunt_id=hunt_id)

    # Prevent creators from inscribing in their own hunts
    if treasure_hunt.creator == request.user:
        messages.error(
            request, "You cannot enroll in a hunt that you have created yourself"
        )
        return redirect("hunt_details", hunt_id=hunt_id)

    # Check if user is already inscribed
    if UserProgress.objects.filter(
        user=request.user, treasure_hunt=treasure_hunt
    ).exists():
        messages.warning(request, "You are already enrolled in this treasure hunt")
        return redirect("hunt_details", hunt_id=hunt_id)

    # Create the inscription
    UserProgress.objects.create(
        user=request.user,
        treasure_hunt=treasure_hunt,
        current_clue=treasure_hunt.clues.first(),
    )

    messages.success(request, "You have successfully enrolled in the treasure hunt!")
    return redirect("hunt_details", hunt_id=hunt_id)


@login_required
def view_hunt_participants(request, hunt_id):
    """
    View function for displaying all participants enrolled in a treasure hunt.
    Only accessible by the hunt creator.
    """
    treasure_hunt = get_object_or_404(TreasureHunt, pk=hunt_id)

    # Check if user is the creator
    if treasure_hunt.creator != request.user:
        messages.error(
            request, "Only the creator can see the participants of the treasure hunt"
        )
        return redirect("hunt_details", hunt_id=hunt_id)

    # Get all participants with their progress
    participants = (
        UserProgress.objects.filter(treasure_hunt=treasure_hunt)
        .select_related("user")
        .order_by("-total_points", "started_at")
    )

    context = {
        "treasure_hunt": treasure_hunt,
        "participants": participants,
    }
    return render(request, "core/hunt_participants.html", context)


@login_required
def hunt_completion(request, hunt_id):
    """
    View function for displaying the completion page of a treasure hunt.
    Shows statistics about the hunt completion.
    """
    treasure_hunt = get_object_or_404(TreasureHunt, pk=hunt_id)
    progress = get_object_or_404(
        UserProgress, user=request.user, treasure_hunt=treasure_hunt
    )

    if not progress.is_completed:
        return redirect("view_hunt", hunt_id=hunt_id)

    # Calculate time taken
    time_taken = progress.completed_at - progress.started_at
    print(time_taken)
    total_seconds = (
        time_taken.total_seconds()
    )  # Use total_seconds to avoid issues with timedelta
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    time_taken_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    print(time_taken_str)

    context = {
        "treasure_hunt": treasure_hunt,
        "time_taken": time_taken_str,
        "total_clues": treasure_hunt.clues.count(),
        "total_points": progress.total_points,
    }
    return render(request, "core/hunt_completion.html", context)

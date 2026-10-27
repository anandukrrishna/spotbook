import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.core.exceptions import ValidationError
from accounts.helpers import user_required, get_current_user_profile, get_current_django_user
from admin_app.models import ParkingLocationTable, ParkingSlotTable, ParkingChargeTable
from user_app.models import BookingTable
from user_app.services import (
    calculate_end_time,
    check_slot_availability,
    get_slots_with_window_status,
    create_booking,
    cancel_booking_record
)

class UserHome(View):
    """
    User landing page & parking location directory with search.
    """
    def get(self, request):
        django_user = get_current_django_user(request)
        user_profile = get_current_user_profile(request)
        search_query = request.GET.get('q', '').strip()
        city_filter = request.GET.get('city', '').strip()

        locations = ParkingLocationTable.objects.filter(is_active=True)
        if search_query:
            locations = locations.filter(name__icontains=search_query) | locations.filter(address__icontains=search_query)
        if city_filter:
            locations = locations.filter(city__iexact=city_filter)

        cities = ParkingLocationTable.objects.filter(is_active=True).values_list('city', flat=True).distinct()

        # Compute user's active bookings count if logged in
        active_bookings_count = 0
        if django_user:
            active_bookings_count = BookingTable.objects.filter(
                user=django_user,
                status__in=['Confirmed', 'Booked', 'Active']
            ).count()

        context = {
            'locations': locations,
            'cities': cities,
            'search_query': search_query,
            'city_filter': city_filter,
            'user_profile': user_profile,
            'active_bookings_count': active_bookings_count,
        }
        return render(request, 'user/user_home.html', context)


class LocationDetail(View):
    """
    Shows slots for a location, with time-window filtering to preview available slots.
    """
    def get(self, request, location_id):
        user_profile = get_current_user_profile(request)
        location = get_object_or_404(ParkingLocationTable, id=location_id, is_active=True)

        today_str = datetime.date.today().strftime('%Y-%m-%d')
        date_str = request.GET.get('date', today_str)
        time_str = request.GET.get('start_time', '10:00')
        duration_str = request.GET.get('duration', '2')

        try:
            booking_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            booking_date = datetime.date.today()
            date_str = today_str

        try:
            start_time = datetime.datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            start_time = datetime.time(10, 0)
            time_str = '10:00'

        try:
            duration = int(duration_str)
            if duration <= 0:
                duration = 1
        except ValueError:
            duration = 2
            duration_str = '2'

        slots_with_status = get_slots_with_window_status(
            location=location,
            date=booking_date,
            start_time=start_time,
            duration_hours=duration
        )

        end_time = calculate_end_time(start_time, duration)
        charges = ParkingChargeTable.objects.filter(status='Active')

        context = {
            'location': location,
            'slots_with_status': slots_with_status,
            'booking_date': date_str,
            'start_time': time_str,
            'duration': duration,
            'end_time': end_time.strftime('%I:%M %p'),
            'user_profile': user_profile,
            'charges': charges,
            'min_date': today_str,
        }
        return render(request, 'user/location_detail.html', context)


class BookSlot(View):
    """
    Handles slot booking creation with strict double-booking prevention.
    """
    def get(self, request, slot_id):
        django_user = get_current_django_user(request)
        if not django_user:
            messages.info(request, "Please log in to book a parking slot.")
            return redirect('login')

        slot = get_object_or_404(ParkingSlotTable, id=slot_id, is_active=True)
        today_str = datetime.date.today().strftime('%Y-%m-%d')

        date_str = request.GET.get('date', today_str)
        time_str = request.GET.get('start_time', '10:00')
        duration_str = request.GET.get('duration', '2')

        try:
            duration = int(duration_str)
        except ValueError:
            duration = 2

        fee = slot.price_per_hour * duration

        context = {
            'slot': slot,
            'location': slot.LOCATIONID,
            'user_profile': get_current_user_profile(request),
            'date_str': date_str,
            'time_str': time_str,
            'duration': duration,
            'fee': fee,
            'min_date': today_str,
        }
        return render(request, 'user/book_slot.html', context)

    def post(self, request, slot_id):
        django_user = get_current_django_user(request)
        if not django_user:
            messages.error(request, "Session expired. Please log in.")
            return redirect('login')

        slot = get_object_or_404(ParkingSlotTable, id=slot_id, is_active=True)

        vehicle_number = request.POST.get('vehicle_number', '').strip()
        vehicle_type = request.POST.get('vehicle_type', 'Car').strip()
        date_str = request.POST.get('date', '').strip()
        time_str = request.POST.get('start_time', '').strip()
        duration_str = request.POST.get('duration', '1').strip()

        today = datetime.date.today()

        try:
            booking_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            if booking_date < today:
                raise ValidationError("Booking date cannot be in the past.")
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('book_slot', slot_id=slot_id)
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))
            return redirect('book_slot', slot_id=slot_id)

        try:
            start_time = datetime.datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            messages.error(request, "Invalid time format.")
            return redirect('book_slot', slot_id=slot_id)

        try:
            duration = int(duration_str)
        except ValueError:
            messages.error(request, "Invalid duration.")
            return redirect('book_slot', slot_id=slot_id)

        if not vehicle_number:
            messages.error(request, "Vehicle registration number is required.")
            return redirect('book_slot', slot_id=slot_id)

        # Attempt atomic reservation with Double-Booking Prevention Engine
        try:
            booking = create_booking(
                user=django_user,
                slot=slot,
                vehicle_number=vehicle_number,
                vehicle_type=vehicle_type,
                date=booking_date,
                start_time=start_time,
                duration_hours=duration
            )
            messages.success(request, f"Parking slot {slot.slot_number} reserved successfully!")
            return redirect('booking_pass', booking_id=booking.id)

        except ValidationError as e:
            err_msg = e.message if hasattr(e, 'message') else str(e)
            messages.error(request, err_msg)
            return redirect('book_slot', slot_id=slot_id)


class BookingPass(View):
    """
    Displays the generated QR Code Pass and booking details.
    """
    def get(self, request, booking_id):
        django_user = get_current_django_user(request)
        is_admin = request.session.get('usertype') == 'admin'

        if not is_admin and not django_user:
            return redirect('login')

        booking = get_object_or_404(BookingTable, id=booking_id)

        # Security check: User can only view their own booking unless admin
        if not is_admin and booking.user != django_user:
            messages.error(request, "Access denied.")
            return redirect('user_home')

        return render(request, 'user/booking_pass.html', {
            'booking': booking,
            'slot': booking.slot,
            'location': booking.slot.LOCATIONID,
            'user_profile': get_current_user_profile(request),
            'is_admin': is_admin,
        })


class MyBookings(View):
    """
    Dashboard for user to view active, upcoming, and past parking bookings.
    """
    def get(self, request):
        django_user = get_current_django_user(request)
        if not django_user:
            messages.info(request, "Please log in to view your bookings.")
            return redirect('login')

        active_bookings = BookingTable.objects.filter(
            user=django_user,
            status__in=['Confirmed', 'Booked', 'Active']
        ).order_by('-booking_date', '-entry_time')

        past_bookings = BookingTable.objects.filter(
            user=django_user,
            status__in=['Completed', 'Cancelled']
        ).order_by('-booking_date', '-entry_time')

        context = {
            'user_profile': get_current_user_profile(request),
            'active_bookings': active_bookings,
            'past_bookings': past_bookings,
        }
        return render(request, 'user/my_bookings.html', context)


class CancelBooking(View):
    """
    Cancels a booking and automatically restores slot availability.
    """
    def post(self, request, booking_id):
        django_user = get_current_django_user(request)
        is_admin = request.session.get('usertype') == 'admin'

        if not is_admin and not django_user:
            return redirect('login')

        booking = get_object_or_404(BookingTable, id=booking_id)

        try:
            cancel_booking_record(booking, user=django_user, is_admin=is_admin)
            messages.success(request, f"Booking #{booking.id} has been cancelled successfully.")
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))

        if is_admin:
            return redirect('Bookings')
        return redirect('my_bookings')


# ---------------------------------------------------------------------------
# Semantic Aliases
# Thin subclasses that expose the task-required view names as proper classes.
# URL names remain unchanged so all {% url '...' %} tags keep working.
# ---------------------------------------------------------------------------

class LocationListView(UserHome):
    """
    Alias for UserHome.
    Lists all active parking locations with search/city filter capabilities.
    Accessible at the user root (/) with URL name 'user_home'.
    """
    pass


class SlotListView(LocationDetail):
    """
    Alias for LocationDetail.
    Shows available parking slots for a chosen location with time-window
    filtering to preview real-time availability before booking.
    Accessible at /location/<location_id>/ with URL name 'location_detail'.
    """
    pass


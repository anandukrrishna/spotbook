import datetime
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from admin_app.models import ParkingSlotTable
from user_app.models import BookingTable

def calculate_end_time(start_time, duration_hours):
    """
    Computes end_time by adding duration_hours to start_time.
    """
    dummy_date = datetime.date(2026, 1, 1)
    start_dt = datetime.datetime.combine(dummy_date, start_time)
    end_dt = start_dt + datetime.timedelta(hours=int(duration_hours))
    return end_dt.time()

def check_slot_availability(slot, date, start_time, end_time, exclude_booking_id=None):
    """
    Critical Double-Booking Prevention Query.
    Checks if any active/booked reservation overlaps with [start_time, end_time) on date.
    Returns (is_available: bool, conflicting_booking: BookingTable or None).
    """
    active_statuses = ['Confirmed', 'Booked', 'Active']

    # Query all active bookings for this slot on this date
    existing_bookings = BookingTable.objects.filter(
        slot=slot,
        booking_date=date,
        status__in=active_statuses
    )

    if exclude_booking_id:
        existing_bookings = existing_bookings.exclude(id=exclude_booking_id)

    for existing in existing_bookings:
        # Standard time overlap logic: (NewStart < ExistEnd) and (NewEnd > ExistStart)
        if (start_time < existing.end_time) and (end_time > existing.entry_time):
            return False, existing

    return True, None

def get_slots_with_window_status(location, date=None, start_time=None, duration_hours=None):
    """
    Returns list of all active slots for a location, annotated with:
    - is_available_for_window (bool)
    - conflict_info (if any)
    """
    slots = ParkingSlotTable.objects.filter(LOCATIONID=location, is_active=True).order_by('slot_number')

    if not date or not start_time or not duration_hours:
        result = []
        for s in slots:
            result.append({
                'slot': s,
                'is_available': s.status == 'Available',
                'conflict': None
            })
        return result

    end_time = calculate_end_time(start_time, duration_hours)
    result = []
    for s in slots:
        is_avail, conflict = check_slot_availability(s, date, start_time, end_time)
        result.append({
            'slot': s,
            'is_available': is_avail,
            'conflict': conflict
        })
    return result

@transaction.atomic
def create_booking(user, slot, vehicle_number, vehicle_type, date, start_time, duration_hours):
    """
    Atomic booking reservation with strict double-booking prevention.
    """
    duration = int(duration_hours)
    if duration <= 0 or duration > 24:
        raise ValidationError("Duration must be between 1 and 24 hours.")

    end_time = calculate_end_time(start_time, duration)

    # Concurrency / overlap check with select_for_update
    locked_slot = ParkingSlotTable.objects.select_for_update().get(id=slot.id)

    is_available, conflict = check_slot_availability(locked_slot, date, start_time, end_time)
    if not is_available:
        conflict_msg = (
            f"Double-Booking Prevented: Slot {locked_slot.slot_number} is already booked from "
            f"{conflict.entry_time.strftime('%I:%M %p')} to {conflict.end_time.strftime('%I:%M %p')} "
            f"on {date}. Please select a different slot or time."
        )
        raise ValidationError(conflict_msg)

    # Fee calculation: duration * slot price per hour
    rate_per_hour = locked_slot.price_per_hour or locked_slot.LOCATIONID.rate_per_hour
    total_fee = Decimal(rate_per_hour) * Decimal(duration)

    booking = BookingTable.objects.create(
        user=user,
        slot=locked_slot,
        booking_date=date,
        entry_time=start_time,
        duration_hours=duration,
        total_fee=total_fee,
        status='Confirmed',
        vehicle_number=vehicle_number.strip().upper() if vehicle_number else '',
        vehicle_type=vehicle_type or 'Car'
    )

    # If the booking date is today, update slot status to Reserved
    today = datetime.date.today()
    if date == today:
        locked_slot.status = 'Reserved'
        locked_slot.save()

    return booking

@transaction.atomic
def cancel_booking_record(booking, user=None, is_admin=False):
    """
    Cancels a booking and frees up slot status if no other active booking exists.
    """
    if not is_admin and booking.user != user:
        raise ValidationError("You do not have permission to cancel this booking.")

    if booking.status in ['Completed', 'Cancelled']:
        raise ValidationError(f"Booking is already {booking.status}.")

    booking.status = 'Cancelled'
    booking.save()

    # Re-evaluate slot status
    slot = booking.slot
    today = datetime.date.today()
    has_active = BookingTable.objects.filter(
        slot=slot,
        booking_date=today,
        status__in=['Confirmed', 'Booked', 'Active']
    ).exists()

    if not has_active and slot.status != 'Occupied':
        slot.status = 'Available'
        slot.save()

    return True

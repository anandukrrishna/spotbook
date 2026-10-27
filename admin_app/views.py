import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from accounts.helpers import admin_required
from accounts.models import UserTable, LoginTable
from admin_app.models import ParkingLocationTable, ParkingSlotTable, ParkingChargeTable, EntryExitTable
from user_app.models import BookingTable
from user_app.services import cancel_booking_record

def parse_booking_ref_to_id(code_str):
    """
    Parses a Booking Ref like 'SB-20261023-0001' or 'SB000001' or '1' into an integer ID.
    """
    if not code_str:
        return None
    code = code_str.strip()
    if 'BOOKING_ID:' in code:
        parts = code.split('|')
        for part in parts:
            if part.startswith('BOOKING_ID:'):
                code = part.split(':', 1)[1].strip()
                break
    if code.startswith('SPOTBOOK:'):
        parts = code.split(':')
        if len(parts) >= 2:
            code = parts[1].strip()

    # Try extracting digits from the end of SB-YYYYMMDD-XXXX
    if '-' in code:
        last_chunk = code.split('-')[-1]
        if last_chunk.isdigit():
            return int(last_chunk)
    
    if code.startswith('SB') and code[2:].isdigit():
        return int(code[2:])

    if code.isdigit():
        return int(code)

    return None


class AdminHome(View):
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        total_users = UserTable.objects.count()
        total_locations = ParkingLocationTable.objects.filter(is_active=True).count()
        total_slots = ParkingSlotTable.objects.filter(is_active=True).count()
        available_slots = ParkingSlotTable.objects.filter(is_active=True, status='Available').count()
        reserved_slots = ParkingSlotTable.objects.filter(is_active=True, status='Reserved').count()
        occupied_slots = ParkingSlotTable.objects.filter(is_active=True, status='Occupied').count()
        total_bookings = BookingTable.objects.count()

        total_revenue = BookingTable.objects.exclude(status='Cancelled').aggregate(Sum('total_fee'))['total_fee__sum'] or Decimal('0.00')

        recent_bookings = BookingTable.objects.select_related('user', 'slot', 'slot__LOCATIONID').order_by('-created_at')[:8]
        currently_parked = BookingTable.objects.filter(status='Active').select_related('user', 'slot', 'slot__LOCATIONID')

        context = {
            'total_users': total_users,
            'total_locations': total_locations,
            'total_slots': total_slots,
            'available_slots': available_slots,
            'reserved_slots': reserved_slots,
            'occupied_slots': occupied_slots,
            'total_bookings': total_bookings,
            'total_revenue': total_revenue,
            'recent_bookings': recent_bookings,
            'currently_parked': currently_parked,
        }
        return render(request, 'admin/admin_home.html', context)


class Users(View):
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        search_query = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', '').strip()

        users = UserTable.objects.select_related('LOGINID').all().order_by('-id')

        if search_query:
            users = users.filter(
                Q(name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(LOGINID__username__icontains=search_query)
            )

        if status_filter == 'active':
            users = users.filter(LOGINID__is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(LOGINID__is_active=False)

        total_users = UserTable.objects.count()
        active_users = UserTable.objects.filter(LOGINID__is_active=True).count()
        inactive_users = total_users - active_users

        context = {
            'users': users,
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'search_query': search_query,
            'status_filter': status_filter,
        }
        return render(request, 'admin/user.html', context)

    def post(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        user_obj = get_object_or_404(UserTable, id=user_id)

        if action == 'toggle_status':
            login_obj = user_obj.LOGINID
            login_obj.is_active = not login_obj.is_active
            login_obj.save()
            status_text = "activated" if login_obj.is_active else "deactivated"
            messages.success(request, f"User {user_obj.name} was {status_text}.")
        elif action == 'delete':
            login_obj = user_obj.LOGINID
            name = user_obj.name
            login_obj.delete()
            messages.success(request, f"User {name} was permanently deleted.")

        return redirect('users')


class ParkingManagement(View):
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')
        return render(request, 'admin/parking_management.html')


class ParkingLocations(View):
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        search_query = request.GET.get('search', '').strip()
        locations = ParkingLocationTable.objects.all().order_by('-id')

        if search_query:
            locations = locations.filter(
                Q(name__icontains=search_query) |
                Q(address__icontains=search_query) |
                Q(city__icontains=search_query)
            )

        total_locs = ParkingLocationTable.objects.count()
        active_locs = ParkingLocationTable.objects.filter(is_active=True).count()
        inactive_locs = total_locs - active_locs

        context = {
            'locations': locations,
            'total_locations': total_locs,
            'active_locations': active_locs,
            'inactive_locations': inactive_locs,
            'search_query': search_query,
        }
        return render(request, 'admin/parking_locations.html', context)

    def post(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        action = request.POST.get('action')

        if action == 'add':
            name = request.POST.get('name', '').strip()
            address = request.POST.get('address', '').strip()
            city = request.POST.get('city', '').strip()
            description = request.POST.get('description', '').strip()
            rate = request.POST.get('rate_per_hour', '50.00').strip()
            total_slots = request.POST.get('total_slots', '0').strip()

            if not name or not address:
                messages.error(request, "Location name and address are required.")
                return redirect('ParkingLocations')

            loc = ParkingLocationTable.objects.create(
                name=name,
                address=address,
                city=city or 'Kozhikode',
                description=description,
                rate_per_hour=Decimal(rate or 50.00),
                total_slots=int(total_slots or 0),
                is_active=True
            )

            if int(total_slots or 0) > 0:
                for i in range(1, int(total_slots) + 1):
                    slot_num = f"S-{i:02d}"
                    ParkingSlotTable.objects.create(
                        LOCATIONID=loc,
                        slot_number=slot_num,
                        slot_type='Car',
                        status='Available',
                        price_per_hour=loc.rate_per_hour
                    )

            messages.success(request, f"Parking Location '{name}' added successfully with {total_slots} slots.")

        elif action == 'edit':
            loc_id = request.POST.get('location_id')
            loc = get_object_or_404(ParkingLocationTable, id=loc_id)
            loc.name = request.POST.get('name', loc.name).strip()
            loc.address = request.POST.get('address', loc.address).strip()
            loc.city = request.POST.get('city', loc.city).strip()
            loc.description = request.POST.get('description', loc.description).strip()
            rate_val = request.POST.get('rate_per_hour')
            if rate_val:
                loc.rate_per_hour = Decimal(rate_val)
            loc.save()
            messages.success(request, f"Location '{loc.name}' updated successfully.")

        elif action == 'toggle_status':
            loc_id = request.POST.get('location_id')
            loc = get_object_or_404(ParkingLocationTable, id=loc_id)
            loc.is_active = not loc.is_active
            loc.save()
            status_text = "activated" if loc.is_active else "deactivated"
            messages.success(request, f"Location '{loc.name}' was {status_text}.")

        elif action == 'delete':
            loc_id = request.POST.get('location_id')
            loc = get_object_or_404(ParkingLocationTable, id=loc_id)
            name = loc.name
            loc.delete()
            messages.success(request, f"Location '{name}' was deleted.")

        return redirect('ParkingLocations')


class ParkingSlots(View):
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        search_query = request.GET.get('search', '').strip()
        location_id = request.GET.get('location', '').strip()
        status_filter = request.GET.get('status', '').strip()

        slots = ParkingSlotTable.objects.select_related('LOCATIONID').filter(is_active=True).order_by('LOCATIONID__name', 'slot_number')

        if search_query:
            slots = slots.filter(slot_number__icontains=search_query)
        if location_id:
            slots = slots.filter(LOCATIONID_id=location_id)
        if status_filter:
            slots = slots.filter(status__iexact=status_filter)

        locations = ParkingLocationTable.objects.filter(is_active=True).order_by('name')

        total_slots = ParkingSlotTable.objects.filter(is_active=True).count()
        available_slots = ParkingSlotTable.objects.filter(is_active=True, status='Available').count()
        reserved_slots = ParkingSlotTable.objects.filter(is_active=True, status='Reserved').count()
        occupied_slots = ParkingSlotTable.objects.filter(is_active=True, status='Occupied').count()

        context = {
            'slots': slots,
            'locations': locations,
            'total_slots': total_slots,
            'available_slots': available_slots,
            'reserved_slots': reserved_slots,
            'occupied_slots': occupied_slots,
            'search_query': search_query,
            'selected_location': location_id,
            'status_filter': status_filter,
        }
        return render(request, 'admin/parking_slots.html', context)

    def post(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        action = request.POST.get('action')

        if action == 'add':
            location_id = request.POST.get('location_id')
            slot_number = request.POST.get('slot_number', '').strip().upper()
            slot_type = request.POST.get('slot_type', 'Car').strip()
            price = request.POST.get('price_per_hour', '50.00').strip()

            location = get_object_or_404(ParkingLocationTable, id=location_id)

            if ParkingSlotTable.objects.filter(LOCATIONID=location, slot_number=slot_number, is_active=True).exists():
                messages.error(request, f"Slot {slot_number} already exists in {location.name}.")
                return redirect('ParkingSlots')

            ParkingSlotTable.objects.create(
                LOCATIONID=location,
                slot_number=slot_number,
                slot_type=slot_type,
                price_per_hour=Decimal(price or 50.00),
                status='Available',
                is_active=True
            )
            messages.success(request, f"Slot {slot_number} added to {location.name}.")

        elif action == 'edit':
            slot_id = request.POST.get('slot_id')
            slot = get_object_or_404(ParkingSlotTable, id=slot_id)
            slot.slot_number = request.POST.get('slot_number', slot.slot_number).strip().upper()
            slot.slot_type = request.POST.get('slot_type', slot.slot_type).strip()
            slot.status = request.POST.get('status', slot.status).strip()
            price_val = request.POST.get('price_per_hour')
            if price_val:
                slot.price_per_hour = Decimal(price_val)
            slot.save()
            messages.success(request, f"Slot {slot.slot_number} updated.")

        elif action == 'update_status':
            slot_id = request.POST.get('slot_id')
            new_status = request.POST.get('status')
            slot = get_object_or_404(ParkingSlotTable, id=slot_id)
            slot.status = new_status
            slot.save()
            messages.success(request, f"Slot {slot.slot_number} status set to {new_status}.")

        elif action == 'delete':
            slot_id = request.POST.get('slot_id')
            slot = get_object_or_404(ParkingSlotTable, id=slot_id)
            num = slot.slot_number
            slot.is_active = False
            slot.save()
            messages.success(request, f"Slot {num} deleted.")

        return redirect('ParkingSlots')


class Bookings(View):
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        search_query = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', '').strip()
        date_filter = request.GET.get('date', '').strip()

        bookings = BookingTable.objects.select_related('user', 'slot', 'slot__LOCATIONID').all().order_by('-created_at')

        if search_query:
            parsed_id = parse_booking_ref_to_id(search_query)
            if parsed_id:
                bookings = bookings.filter(
                    Q(id=parsed_id) |
                    Q(user__username__icontains=search_query) |
                    Q(vehicle_number__icontains=search_query) |
                    Q(slot__slot_number__icontains=search_query)
                )
            else:
                bookings = bookings.filter(
                    Q(user__username__icontains=search_query) |
                    Q(user__first_name__icontains=search_query) |
                    Q(vehicle_number__icontains=search_query) |
                    Q(slot__slot_number__icontains=search_query)
                )

        if status_filter:
            bookings = bookings.filter(status__iexact=status_filter)

        if date_filter:
            bookings = bookings.filter(booking_date=date_filter)

        total_bookings = BookingTable.objects.count()
        upcoming_bookings = BookingTable.objects.filter(status__in=['Confirmed', 'Booked']).count()
        active_bookings = BookingTable.objects.filter(status='Active').count()
        completed_bookings = BookingTable.objects.filter(status='Completed').count()
        cancelled_bookings = BookingTable.objects.filter(status='Cancelled').count()

        context = {
            'bookings': bookings,
            'total_bookings': total_bookings,
            'upcoming_bookings': upcoming_bookings,
            'active_bookings': active_bookings,
            'completed_bookings': completed_bookings,
            'cancelled_bookings': cancelled_bookings,
            'search_query': search_query,
            'status_filter': status_filter,
            'date_filter': date_filter,
        }
        return render(request, 'admin/bookings.html', context)

    def post(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        action = request.POST.get('action')
        booking_id = request.POST.get('booking_id')
        booking = get_object_or_404(BookingTable, id=booking_id)

        if action == 'cancel':
            cancel_booking_record(booking, is_admin=True)
            messages.success(request, f"Booking #{booking.id} cancelled.")

        return redirect('Bookings')


class ParkingCharges(View):
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        charges = ParkingChargeTable.objects.select_related('LOCATIONID').all().order_by('-id')
        locations = ParkingLocationTable.objects.filter(is_active=True).order_by('name')

        total_charges = charges.count()
        active_charges = charges.filter(status='Active').count()
        inactive_charges = total_charges - active_charges

        context = {
            'charges': charges,
            'locations': locations,
            'total_charges': total_charges,
            'active_charges': active_charges,
            'inactive_charges': inactive_charges,
        }
        return render(request, 'admin/parking_charges.html', context)

    def post(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        action = request.POST.get('action')

        if action == 'add':
            vehicle_type = request.POST.get('vehicle_type', 'Car').strip()
            charge_type = request.POST.get('charge_type', 'Hourly').strip()
            rate = request.POST.get('rate', '50.00').strip()
            description = request.POST.get('description', '').strip()
            location_id = request.POST.get('location_id')

            location = None
            if location_id:
                location = ParkingLocationTable.objects.filter(id=location_id).first()

            ParkingChargeTable.objects.create(
                LOCATIONID=location,
                vehicle_type=vehicle_type,
                charge_type=charge_type,
                rate=Decimal(rate or 50.00),
                description=description,
                status='Active'
            )
            messages.success(request, f"Parking charge rule for {vehicle_type} added.")

        elif action == 'edit':
            charge_id = request.POST.get('charge_id')
            charge = get_object_or_404(ParkingChargeTable, id=charge_id)
            charge.vehicle_type = request.POST.get('vehicle_type', charge.vehicle_type)
            charge.charge_type = request.POST.get('charge_type', charge.charge_type)
            charge.rate = Decimal(request.POST.get('rate', charge.rate))
            charge.description = request.POST.get('description', charge.description)
            charge.status = request.POST.get('status', charge.status)
            charge.save()
            messages.success(request, "Parking charge rule updated.")

        elif action == 'delete':
            charge_id = request.POST.get('charge_id')
            charge = get_object_or_404(ParkingChargeTable, id=charge_id)
            charge.delete()
            messages.success(request, "Parking charge rule deleted.")

        return redirect('ParkingCharges')


class QRVerification(View):
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        total_attempts = BookingTable.objects.count()
        verified_count = BookingTable.objects.filter(status__in=['Active', 'Completed']).count()
        awaiting_count = BookingTable.objects.filter(status__in=['Confirmed', 'Booked']).count()

        query_code = request.GET.get('qr_code', '').strip()
        matched_booking = None
        verification_status = 'Not Checked'
        status_message = ''

        if query_code:
            parsed_id = parse_booking_ref_to_id(query_code)
            if parsed_id:
                matched_booking = BookingTable.objects.filter(id=parsed_id).select_related('user', 'slot', 'slot__LOCATIONID').first()
            if not matched_booking:
                matched_booking = BookingTable.objects.filter(
                    Q(vehicle_number__iexact=query_code)
                ).select_related('user', 'slot', 'slot__LOCATIONID').first()

            if matched_booking:
                if matched_booking.status in ['Confirmed', 'Booked']:
                    verification_status = 'Valid'
                    status_message = 'Booking is confirmed and awaiting vehicle entry.'
                elif matched_booking.status == 'Active':
                    verification_status = 'Already Entered'
                    status_message = 'Vehicle is currently parked inside.'
                elif matched_booking.status == 'Completed':
                    verification_status = 'Completed'
                    status_message = 'Booking has already been completed.'
                elif matched_booking.status == 'Cancelled':
                    verification_status = 'Cancelled'
                    status_message = 'This booking was cancelled.'
            else:
                verification_status = 'Invalid'
                status_message = 'No booking found matching this QR code or Booking ID.'

        context = {
            'total_attempts': total_attempts,
            'verified_count': verified_count,
            'awaiting_count': awaiting_count,
            'query_code': query_code,
            'matched_booking': matched_booking,
            'verification_status': verification_status,
            'status_message': status_message,
        }
        return render(request, 'admin/qr_verification.html', context)

    def post(self, request):
        qr_code = request.POST.get('qr_code', '').strip()
        from django.urls import reverse
        return redirect(reverse('QRVerification') + f'?qr_code={qr_code}')


class VehicleManagement(View):
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')
        return render(request, 'admin/vehicle_management.html')


class VehicleEntry(View):
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        today = datetime.date.today()
        search_id = request.GET.get('booking_id', '').strip()

        matched_booking = None
        if search_id:
            parsed_id = parse_booking_ref_to_id(search_id)
            if parsed_id:
                matched_booking = BookingTable.objects.filter(id=parsed_id).select_related('user', 'slot', 'slot__LOCATIONID').first()
            if not matched_booking:
                matched_booking = BookingTable.objects.filter(
                    Q(vehicle_number__iexact=search_id)
                ).select_related('user', 'slot', 'slot__LOCATIONID').first()

        entered_today = EntryExitTable.objects.filter(entry_time__date=today).count()
        vehicles_inside = BookingTable.objects.filter(status='Active').count()
        awaiting_entry = BookingTable.objects.filter(booking_date=today, status__in=['Confirmed', 'Booked']).count()

        recent_entries = EntryExitTable.objects.select_related(
            'BOOKINGID', 'BOOKINGID__user', 'BOOKINGID__slot', 'BOOKINGID__slot__LOCATIONID'
        ).filter(entry_time__isnull=False).order_by('-entry_time')[:10]

        context = {
            'entered_today': entered_today,
            'vehicles_inside': vehicles_inside,
            'awaiting_entry': awaiting_entry,
            'search_id': search_id,
            'matched_booking': matched_booking,
            'recent_entries': recent_entries,
            'current_time_str': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
        }
        return render(request, 'admin/vehicle_entry.html', context)

    def post(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        booking_code = request.POST.get('booking_id', '').strip()
        entry_time_str = request.POST.get('entry_time')

        parsed_id = parse_booking_ref_to_id(booking_code)
        booking = None
        if parsed_id:
            booking = BookingTable.objects.filter(id=parsed_id).first()
        if not booking:
            booking = BookingTable.objects.filter(vehicle_number__iexact=booking_code).first()

        if not booking:
            messages.error(request, f"Booking '{booking_code}' not found.")
            return redirect('VehicleEntry')

        if booking.status == 'Active':
            messages.warning(request, f"Vehicle for Booking #{booking.id} has already entered!")
            return redirect('VehicleEntry')

        if booking.status in ['Completed', 'Cancelled']:
            messages.error(request, f"Cannot record entry: Booking is already {booking.status}.")
            return redirect('VehicleEntry')

        entry_dt = timezone.now()
        if entry_time_str:
            try:
                entry_dt = datetime.datetime.strptime(entry_time_str, '%Y-%m-%dT%H:%M')
                entry_dt = timezone.make_aware(entry_dt)
            except Exception:
                pass

        booking.status = 'Active'
        booking.save()

        slot = booking.slot
        slot.status = 'Occupied'
        slot.save()

        EntryExitTable.objects.create(
            BOOKINGID=booking,
            entry_time=entry_dt,
            notes='Gate entry recorded'
        )

        messages.success(request, f"Vehicle entry confirmed for Booking #{booking.id}! Slot {slot.slot_number} marked Occupied.")
        return redirect('VehicleEntry')


class VehicleExit(View):
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        today = datetime.date.today()
        search_id = request.GET.get('booking_id', '').strip()

        matched_booking = None
        if search_id:
            parsed_id = parse_booking_ref_to_id(search_id)
            if parsed_id:
                matched_booking = BookingTable.objects.filter(id=parsed_id, status='Active').select_related('user', 'slot', 'slot__LOCATIONID').first()
            if not matched_booking:
                matched_booking = BookingTable.objects.filter(
                    Q(vehicle_number__iexact=search_id),
                    status='Active'
                ).select_related('user', 'slot', 'slot__LOCATIONID').first()

        exited_today = EntryExitTable.objects.filter(exit_time__date=today).count()
        vehicles_inside = BookingTable.objects.filter(status='Active').count()
        completed_sessions = BookingTable.objects.filter(status='Completed').count()

        parked_vehicles = BookingTable.objects.filter(status='Active').select_related(
            'user', 'slot', 'slot__LOCATIONID'
        ).order_by('-booking_date')

        recent_exits = EntryExitTable.objects.select_related(
            'BOOKINGID', 'BOOKINGID__user', 'BOOKINGID__slot', 'BOOKINGID__slot__LOCATIONID'
        ).filter(exit_time__isnull=False).order_by('-exit_time')[:10]

        context = {
            'exited_today': exited_today,
            'vehicles_inside': vehicles_inside,
            'completed_sessions': completed_sessions,
            'search_id': search_id,
            'matched_booking': matched_booking,
            'parked_vehicles': parked_vehicles,
            'recent_exits': recent_exits,
            'current_time_str': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
        }
        return render(request, 'admin/vehicle_exit.html', context)

    def post(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        booking_code = request.POST.get('booking_id', '').strip()
        exit_time_str = request.POST.get('exit_time')

        parsed_id = parse_booking_ref_to_id(booking_code)
        booking = None
        if parsed_id:
            booking = BookingTable.objects.filter(id=parsed_id).first()
        if not booking:
            booking = BookingTable.objects.filter(vehicle_number__iexact=booking_code).first()

        if not booking:
            messages.error(request, f"Booking '{booking_code}' not found.")
            return redirect('VehicleExit')

        if booking.status != 'Active':
            messages.error(request, f"Cannot record exit: Booking is not currently Active (Status: {booking.status}).")
            return redirect('VehicleExit')

        exit_dt = timezone.now()
        if exit_time_str:
            try:
                exit_dt = datetime.datetime.strptime(exit_time_str, '%Y-%m-%dT%H:%M')
                exit_dt = timezone.make_aware(exit_dt)
            except Exception:
                pass

        booking.status = 'Completed'
        booking.save()

        slot = booking.slot
        slot.status = 'Available'
        slot.save()

        log_entry = EntryExitTable.objects.filter(BOOKINGID=booking).order_by('-id').first()
        if log_entry:
            log_entry.exit_time = exit_dt
            log_entry.notes = 'Gate exit recorded'
            log_entry.save()
        else:
            EntryExitTable.objects.create(
                BOOKINGID=booking,
                exit_time=exit_dt,
                notes='Gate exit recorded'
            )

        messages.success(request, f"Vehicle exit confirmed for Booking #{booking.id}! Slot {slot.slot_number} is now Available.")
        return redirect('VehicleExit')


class Reports(View):
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        total_bookings = BookingTable.objects.count()
        total_slots = ParkingSlotTable.objects.filter(is_active=True).count()
        total_locations = ParkingLocationTable.objects.filter(is_active=True).count()
        total_revenue = BookingTable.objects.exclude(status='Cancelled').aggregate(Sum('total_fee'))['total_fee__sum'] or Decimal('0.00')

        bookings_by_status = BookingTable.objects.values('status').annotate(count=Count('id'))

        location_stats = []
        for loc in ParkingLocationTable.objects.filter(is_active=True):
            slot_cnt = loc.parkingslottable_set.filter(is_active=True).count()
            booking_cnt = BookingTable.objects.filter(slot__LOCATIONID=loc).count()
            rev = BookingTable.objects.filter(slot__LOCATIONID=loc).exclude(status='Cancelled').aggregate(Sum('total_fee'))['total_fee__sum'] or Decimal('0.00')
            location_stats.append({
                'location': loc,
                'slot_count': slot_cnt,
                'booking_count': booking_cnt,
                'revenue': rev,
            })

        entry_exit_logs = EntryExitTable.objects.select_related(
            'BOOKINGID', 'BOOKINGID__user', 'BOOKINGID__slot', 'BOOKINGID__slot__LOCATIONID'
        ).order_by('-id')[:15]

        context = {
            'total_bookings': total_bookings,
            'total_slots': total_slots,
            'total_locations': total_locations,
            'total_revenue': total_revenue,
            'bookings_by_status': bookings_by_status,
            'location_stats': location_stats,
            'entry_exit_logs': entry_exit_logs,
        }
        return render(request, 'admin/reports.html', context)


# ---------------------------------------------------------------------------
# Semantic Aliases
# These thin subclasses expose the task-required view names without changing
# any existing URL names, so all existing `{% url '...' %}` tags keep working.
# ---------------------------------------------------------------------------

class AdminDashboard(AdminHome):
    """
    Alias for AdminHome. Accessible at /admin_app/dashboard/
    with URL name 'admin_dashboard'. Renders the same aggregated
    statistics dashboard — Users, Locations, Slots, Revenue, Recent Activity.
    """
    pass


class GateOperations(View):
    """
    Unified Gate Operations terminal.
    GET  → renders a hub page linking to VehicleEntry and VehicleExit.
    Staff can choose to record Vehicle Entry or Vehicle Exit from one place.
    Accessible at /admin_app/gate/ with URL name 'gate_operations'.
    """
    def get(self, request):
        if request.session.get('usertype') != 'admin':
            return redirect('login')

        today = datetime.date.today()
        vehicles_inside = BookingTable.objects.filter(status='Active').count()
        awaiting_entry = BookingTable.objects.filter(
            booking_date=today, status__in=['Confirmed', 'Booked']
        ).count()
        exited_today = EntryExitTable.objects.filter(exit_time__date=today).count()
        entered_today = EntryExitTable.objects.filter(entry_time__date=today).count()

        recent_activity = EntryExitTable.objects.select_related(
            'BOOKINGID', 'BOOKINGID__user', 'BOOKINGID__slot', 'BOOKINGID__slot__LOCATIONID'
        ).order_by('-id')[:12]

        context = {
            'vehicles_inside': vehicles_inside,
            'awaiting_entry': awaiting_entry,
            'exited_today': exited_today,
            'entered_today': entered_today,
            'recent_activity': recent_activity,
        }
        return render(request, 'admin/gate_operations.html', context)
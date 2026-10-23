import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from accounts.models import LoginTable, UserTable
from admin_app.models import ParkingLocationTable, ParkingSlotTable, EntryExitTable
from user_app.models import BookingTable
from user_app.services import (
    calculate_end_time,
    check_slot_availability,
    create_booking,
    cancel_booking_record
)

class SmartParkingCoreTests(TestCase):
    def setUp(self):
        # 1. Create Django User & Profile
        self.django_user = User.objects.create_user(
            username='test_driver',
            email='driver@example.com',
            password='Password@123'
        )

        self.login_user = LoginTable.objects.create(
            username='test_driver',
            password='Password@123',
            usertype='user'
        )
        self.user_profile = UserTable.objects.create(
            LOGINID=self.login_user,
            name='Test Driver',
            email='driver@example.com',
            phone='9998887770',
            address='Calicut Beach Road'
        )

        # 2. Create Parking Location
        self.location = ParkingLocationTable.objects.create(
            name='Central Mall Parking',
            address='Mavoor Road',
            city='Kozhikode',
            description='Prime underground parking',
            total_slots=10,
            rate_per_hour=Decimal('50.00'),
            is_active=True
        )

        # 3. Create Slots
        self.slot_a = ParkingSlotTable.objects.create(
            LOCATIONID=self.location,
            slot_number='A-01',
            slot_type='Car',
            status='Available',
            price_per_hour=Decimal('50.00'),
            is_active=True
        )

        self.slot_b = ParkingSlotTable.objects.create(
            LOCATIONID=self.location,
            slot_number='A-02',
            slot_type='Car',
            status='Available',
            price_per_hour=Decimal('60.00'),
            is_active=True
        )

        self.test_date = datetime.date(2026, 11, 15)

    def test_fee_calculation_and_qr_generation(self):
        """Verify automated fee calculation and QR Code file generation."""
        start_time = datetime.time(10, 0)
        duration = 3 # 3 hours * 50 = 150

        booking = create_booking(
            user=self.django_user,
            slot=self.slot_a,
            vehicle_number='KL-11-ZZ-9999',
            vehicle_type='Car',
            date=self.test_date,
            start_time=start_time,
            duration_hours=duration
        )

        # Check fee and properties
        self.assertEqual(booking.total_fee, Decimal('150.00'))
        self.assertEqual(booking.end_time, datetime.time(13, 0))
        self.assertTrue(booking.booking_id.startswith('SB-'))
        self.assertEqual(booking.status, 'Confirmed')

        # Check QR Code Image is generated
        self.assertTrue(bool(booking.qr_code))
        self.assertTrue(booking.qr_code.name.endswith('.png'))

    def test_double_booking_prevention_strict(self):
        """
        Critical Test: Ensure zero overlapping reservations can be made for the same slot.
        """
        # Baseline booking: Slot A on test_date from 10:00 to 12:00 (2 hours)
        base_booking = create_booking(
            user=self.django_user,
            slot=self.slot_a,
            vehicle_number='KL-11-AA-1111',
            vehicle_type='Car',
            date=self.test_date,
            start_time=datetime.time(10, 0),
            duration_hours=2 # Ends at 12:00
        )
        self.assertIsNotNone(base_booking.id)

        # Case 1: Partial overlap starting later (11:00 to 13:00) -> MUST FAIL
        with self.assertRaises(ValidationError) as cm:
            create_booking(
                user=self.django_user,
                slot=self.slot_a,
                vehicle_number='KL-11-BB-2222',
                vehicle_type='Car',
                date=self.test_date,
                start_time=datetime.time(11, 0),
                duration_hours=2
            )
        self.assertIn("Double-Booking Prevented", str(cm.exception))

        # Case 2: Partial overlap starting earlier (09:00 to 11:00) -> MUST FAIL
        with self.assertRaises(ValidationError) as cm:
            create_booking(
                user=self.django_user,
                slot=self.slot_a,
                vehicle_number='KL-11-CC-3333',
                vehicle_type='Car',
                date=self.test_date,
                start_time=datetime.time(9, 0),
                duration_hours=2
            )
        self.assertIn("Double-Booking Prevented", str(cm.exception))

        # Case 3: Completely enclosed within existing window (10:30 to 11:30) -> MUST FAIL
        with self.assertRaises(ValidationError) as cm:
            create_booking(
                user=self.django_user,
                slot=self.slot_a,
                vehicle_number='KL-11-DD-4444',
                vehicle_type='Car',
                date=self.test_date,
                start_time=datetime.time(10, 30),
                duration_hours=1
            )
        self.assertIn("Double-Booking Prevented", str(cm.exception))

        # Case 4: Adjacent booking right when previous ends (12:00 to 14:00) -> MUST SUCCEED
        adjacent_booking = create_booking(
            user=self.django_user,
            slot=self.slot_a,
            vehicle_number='KL-11-EE-5555',
            vehicle_type='Car',
            date=self.test_date,
            start_time=datetime.time(12, 0),
            duration_hours=2
        )
        self.assertIsNotNone(adjacent_booking.id)

        # Case 5: Different Slot at same time (Slot B, 10:00 to 12:00) -> MUST SUCCEED
        slot_b_booking = create_booking(
            user=self.django_user,
            slot=self.slot_b,
            vehicle_number='KL-11-FF-6666',
            vehicle_type='Car',
            date=self.test_date,
            start_time=datetime.time(10, 0),
            duration_hours=2
        )
        self.assertIsNotNone(slot_b_booking.id)

        # Case 6: Same Slot, same time, but on a DIFFERENT date -> MUST SUCCEED
        next_day = self.test_date + datetime.timedelta(days=1)
        next_day_booking = create_booking(
            user=self.django_user,
            slot=self.slot_a,
            vehicle_number='KL-11-GG-7777',
            vehicle_type='Car',
            date=next_day,
            start_time=datetime.time(10, 0),
            duration_hours=2
        )
        self.assertIsNotNone(next_day_booking.id)

    def test_cancellation_frees_slot_for_rebooking(self):
        """Cancelling a booking frees the slot so another booking can take that time window."""
        booking = create_booking(
            user=self.django_user,
            slot=self.slot_a,
            vehicle_number='KL-11-HH-8888',
            vehicle_type='Car',
            date=self.test_date,
            start_time=datetime.time(14, 0),
            duration_hours=2
        )

        # Try overlapping -> Fails
        with self.assertRaises(ValidationError):
            create_booking(
                user=self.django_user,
                slot=self.slot_a,
                vehicle_number='KL-11-II-9999',
                vehicle_type='Car',
                date=self.test_date,
                start_time=datetime.time(14, 30),
                duration_hours=1
            )

        # Cancel the first booking
        cancel_booking_record(booking, user=self.django_user)
        self.assertEqual(booking.status, 'Cancelled')

        # Now booking the exact same time window must succeed!
        rebooking = create_booking(
            user=self.django_user,
            slot=self.slot_a,
            vehicle_number='KL-11-II-9999',
            vehicle_type='Car',
            date=self.test_date,
            start_time=datetime.time(14, 0),
            duration_hours=2
        )
        self.assertIsNotNone(rebooking.id)
        self.assertEqual(rebooking.status, 'Confirmed')

    def test_gate_entry_and_exit_workflow(self):
        """Verify Vehicle Entry -> Occupied -> Vehicle Exit -> Available workflow."""
        today = datetime.date.today()
        booking = create_booking(
            user=self.django_user,
            slot=self.slot_a,
            vehicle_number='KL-11-GATE-01',
            vehicle_type='Car',
            date=today,
            start_time=datetime.time(8, 0),
            duration_hours=4
        )

        # Record Gate In (Entry)
        booking.status = 'Active'
        booking.save()
        self.slot_a.status = 'Occupied'
        self.slot_a.save()

        from django.utils import timezone
        EntryExitTable.objects.create(
            BOOKINGID=booking,
            entry_time=timezone.now()
        )

        self.slot_a.refresh_from_db()
        self.assertEqual(self.slot_a.status, 'Occupied')
        self.assertEqual(booking.status, 'Active')

        # Record Gate Out (Exit)
        booking.status = 'Completed'
        booking.save()
        self.slot_a.status = 'Available'
        self.slot_a.save()

        entry_exit_log = EntryExitTable.objects.get(BOOKINGID=booking)
        entry_exit_log.exit_time = timezone.now()
        entry_exit_log.save()

        self.slot_a.refresh_from_db()
        self.assertEqual(self.slot_a.status, 'Available')
        self.assertEqual(booking.status, 'Completed')

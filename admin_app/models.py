from django.db import models




# Create your models here.

class ParkingLocationTable(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100, default='Kozhikode')
    description = models.TextField(blank=True, default='')
    total_slots = models.IntegerField(default=0)
    rate_per_hour = models.DecimalField(max_digits=6, decimal_places=2, default=50.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.city})"

    @property
    def total_slots_count(self):
        count = self.parkingslottable_set.filter(is_active=True).count()
        return count if count > 0 else self.total_slots

    @property
    def available_slots_count(self):
        return self.parkingslottable_set.filter(is_active=True, status='Available').count()

    @property
    def reserved_slots_count(self):
        return self.parkingslottable_set.filter(is_active=True, status='Reserved').count()

    @property
    def occupied_slots_count(self):
        return self.parkingslottable_set.filter(is_active=True, status='Occupied').count()


class ParkingSlotTable(models.Model):
    STATUS_CHOICES = (
        ('Available', 'Available'),
        ('Reserved', 'Reserved'),
        ('Occupied', 'Occupied'),
    )
    LOCATIONID = models.ForeignKey(ParkingLocationTable, on_delete=models.CASCADE)
    slot_number = models.CharField(max_length=10)
    slot_type = models.CharField(max_length=20, default="Car") # Car, Bike, EV
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Available")
    price_per_hour = models.DecimalField(max_digits=6, decimal_places=2, default=50.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.LOCATIONID.name} - Slot {self.slot_number} ({self.status})"


class ParkingChargeTable(models.Model):
    LOCATIONID = models.ForeignKey(ParkingLocationTable, on_delete=models.CASCADE, null=True, blank=True)
    vehicle_type = models.CharField(max_length=50, default="Car")
    charge_type = models.CharField(max_length=50, default="Hourly")
    rate = models.DecimalField(max_digits=6, decimal_places=2, default=50.00)
    description = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=20, default="Active")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        loc = self.LOCATIONID.name if self.LOCATIONID else "Global"
        return f"{loc} - {self.vehicle_type}: ₹{self.rate}/{self.charge_type}"


class EntryExitTable(models.Model):
    BOOKINGID = models.ForeignKey("user_app.BookingTable", on_delete=models.CASCADE)
    entry_time = models.DateTimeField(null=True, blank=True)
    exit_time = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return f"EntryExit for Booking #{self.BOOKINGID_id}"
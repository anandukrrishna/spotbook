import io
import os
import random
import qrcode
from django.core.files.base import ContentFile
from django.db import models
from accounts.models import UserTable
from admin_app.models import ParkingSlotTable

class BookingTable(models.Model):
    STATUS_CHOICES = (
        ('Booked', 'Booked'),        # Reserved upcoming booking
        ('Active', 'Active'),        # Vehicle entered / Currently parked
        ('Completed', 'Completed'),  # Vehicle exited
        ('Cancelled', 'Cancelled'),  # Cancelled
    )

    booking_id = models.CharField(max_length=30, unique=True, blank=True, null=True)
    USERID = models.ForeignKey(UserTable, on_delete=models.CASCADE)
    SLOTID = models.ForeignKey(ParkingSlotTable, on_delete=models.CASCADE)
    vehicle_number = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=20, default="Car")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_hours = models.IntegerField(default=1)
    fee = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Booked")
    qr_code = models.CharField(max_length=150, blank=True)
    qr_code_image = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"Booking #{self.booking_id or self.id} - {self.SLOTID.slot_number} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.booking_id:
            rand_suffix = ''.join(random.choices('0123456789ABCDEF', k=6))
            date_str = self.date.strftime('%Y%m%d') if self.date else '20261023'
            self.booking_id = f"SB-{date_str}-{rand_suffix}"

        if not self.qr_code:
            self.qr_code = f"SPOTBOOK:{self.booking_id}:{self.vehicle_number}"

        # If image not generated yet, generate QR Code with Pillow & qrcode
        if not self.qr_code_image:
            qr_content = f"SPOTBOOK_PASS|BOOKING_ID:{self.booking_id}|SLOT:{self.SLOTID.slot_number}|LOC:{self.SLOTID.LOCATIONID.name}|DATE:{self.date}|START:{self.start_time}|END:{self.end_time}|VEHICLE:{self.vehicle_number}"
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            qr.add_data(qr_content)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#1e3a8a", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            file_name = f"qr_{self.booking_id}.png"
            self.qr_code_image.save(file_name, ContentFile(buffer.getvalue()), save=False)

        super().save(*args, **kwargs)
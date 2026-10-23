import io
import os
import datetime
import qrcode
from django.core.files.base import ContentFile
from django.db import models
from django.contrib.auth.models import User
from admin_app.models import ParkingSlotTable

class BookingTable(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    slot = models.ForeignKey(ParkingSlotTable, on_delete=models.CASCADE)
    booking_date = models.DateField()
    entry_time = models.TimeField()
    duration_hours = models.IntegerField()
    total_fee = models.DecimalField(max_digits=8, decimal_places=2)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    status = models.CharField(max_length=20, default='Confirmed') # Confirmed, Cancelled, Completed
    created_at = models.DateTimeField(auto_now_add=True)
    vehicle_number = models.CharField(max_length=20, blank=True, default='')
    vehicle_type = models.CharField(max_length=20, default='Car')

    def __str__(self):
        return f"Booking #{self.id} - {self.user.username} - Slot {self.slot.slot_number}"

    @property
    def USERID(self):
        return self.user

    @property
    def SLOTID(self):
        return self.slot

    @property
    def date(self):
        return self.booking_date

    @property
    def start_time(self):
        return self.entry_time

    @property
    def fee(self):
        return self.total_fee

    @property
    def qr_code_image(self):
        return self.qr_code

    @property
    def booking_id(self):
        date_str = self.booking_date.strftime('%Y%m%d') if self.booking_date else '20261023'
        return f"SB-{date_str}-{self.id:04d}" if self.id else f"SB-{date_str}-PENDING"

    @property
    def end_time(self):
        dummy_date = datetime.date(2026, 1, 1)
        start_dt = datetime.datetime.combine(dummy_date, self.entry_time)
        end_dt = start_dt + datetime.timedelta(hours=int(self.duration_hours or 1))
        return end_dt.time()

    def generate_qr(self):
        qr_content = f"SPOTBOOK_PASS|BOOKING_ID:{self.booking_id}|SLOT:{self.slot.slot_number}|LOC:{self.slot.LOCATIONID.name}|DATE:{self.booking_date}|ENTRY:{self.entry_time}|DURATION:{self.duration_hours}H|FEE:{self.total_fee}|USER:{self.user.username}"
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
        file_name = f"qr_SB_{self.id or 'temp'}.png"
        self.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=False)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.qr_code:
            self.generate_qr()
            super().save(update_fields=['qr_code'])
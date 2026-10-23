from django.urls import path
from user_app.views import (
    UserHome,
    LocationDetail,
    BookSlot,
    BookingPass,
    MyBookings,
    CancelBooking
)

urlpatterns = [
    path('', UserHome.as_view(), name='user_home'),
    path('location/<int:location_id>/', LocationDetail.as_view(), name='location_detail'),
    path('book/<int:slot_id>/', BookSlot.as_view(), name='book_slot'),
    path('booking/pass/<int:booking_id>/', BookingPass.as_view(), name='booking_pass'),
    path('my-bookings/', MyBookings.as_view(), name='my_bookings'),
    path('booking/cancel/<int:booking_id>/', CancelBooking.as_view(), name='cancel_booking'),
]

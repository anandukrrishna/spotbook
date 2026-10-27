"""
URL configuration for user_app.

Maps all user-facing views: Location listing, slot browsing, booking creation,
QR pass display, booking management (view, cancel), and semantic alias URLs.
"""
from django.urls import path
from user_app.views import (
    # Primary views
    UserHome,
    LocationDetail,
    BookSlot,
    BookingPass,
    MyBookings,
    CancelBooking,
    # Semantic aliases (task-required class names)
    LocationListView,
    SlotListView,
)

urlpatterns = [
    # --- Core user-facing routes ---
    path('', UserHome.as_view(), name='user_home'),
    path('location/<int:location_id>/', LocationDetail.as_view(), name='location_detail'),
    path('book/<int:slot_id>/', BookSlot.as_view(), name='book_slot'),
    path('booking/pass/<int:booking_id>/', BookingPass.as_view(), name='booking_pass'),
    path('my-bookings/', MyBookings.as_view(), name='my_bookings'),
    path('booking/cancel/<int:booking_id>/', CancelBooking.as_view(), name='cancel_booking'),

    # --- Semantic alias routes (same logic, descriptive names) ---
    path('locations/', LocationListView.as_view(), name='location_list'),
    path('slots/<int:location_id>/', SlotListView.as_view(), name='slot_list'),
]

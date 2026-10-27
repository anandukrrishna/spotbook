"""
URL configuration for admin_app.

Maps all admin-facing views: Dashboard, User Management, Parking Locations/Slots/Charges,
Booking Management, QR Verification, Gate Operations (Vehicle Entry/Exit), and Reports.
"""
from django.urls import path
from admin_app.views import (
    AdminHome,
    AdminDashboard,
    Users,
    ParkingManagement,
    ParkingLocations,
    ParkingSlots,
    Bookings,
    ParkingCharges,
    QRVerification,
    GateOperations,
    VehicleManagement,
    VehicleEntry,
    VehicleExit,
    Reports,
)

urlpatterns = [
    # Dashboard — primary & alias
    path('AdminHome', AdminHome.as_view(), name='admin_home'),
    path('dashboard/', AdminDashboard.as_view(), name='admin_dashboard'),

    # User Management
    path('users/', Users.as_view(), name='users'),

    # Parking Management
    path('parking/', ParkingManagement.as_view(), name='parking_management'),
    path('parking/locations/', ParkingLocations.as_view(), name='ParkingLocations'),
    path('parking/slots/', ParkingSlots.as_view(), name='ParkingSlots'),
    path('parking-charges/', ParkingCharges.as_view(), name='ParkingCharges'),

    # Booking Management
    path('bookings/', Bookings.as_view(), name='Bookings'),

    # QR Verification & Gate Operations
    path('qr-verification/', QRVerification.as_view(), name='QRVerification'),
    path('gate/', GateOperations.as_view(), name='gate_operations'),  # unified gate terminal
    path('vehicle-management/', VehicleManagement.as_view(), name='VehicleManagement'),
    path('vehicle/entry/', VehicleEntry.as_view(), name='VehicleEntry'),
    path('vehicle/exit/', VehicleExit.as_view(), name='VehicleExit'),

    # Reports & Analytics
    path('reports/', Reports.as_view(), name='Reports'),
]

from django.shortcuts import render
from django.views import View

# Create your views here.

class AdminHome(View):

    def get(self, request):
        return render(request, 'admin/admin_home.html')


class Users(View):

    def get(self, request):
        return render(request, 'admin/user.html')


class ParkingManagement(View):

    def get(self, request):
        return render(request, 'admin/parking_management.html')

class ParkingLocations(View):

    def get(self, request):
        return render(request, 'admin/parking_locations.html')


class ParkingSlots(View):

    def get(self, request):
        return render(request, 'admin/parking_slots.html')

class Bookings(View):

    def get(self, request):
        return render(request, 'admin/bookings.html')

class ParkingCharges(View):
    def get(self, request):
        return render(request, 'admin/parking_charges.html')

class QRVerification(View):
    def get(self, request):
        return render(
            request,
            'admin/qr_verification.html'
        )

class VehicleManagement(View):
    def get(self, request):
        return render(
            request,
            'admin/vehicle_management.html'
        )

class VehicleEntry(View):
    def get(self, request):
        return render(request, 'admin/vehicle_entry.html')

    def post(self, request):
        return render(request, 'admin/vehicle_entry.html')


class VehicleExit(View):
    def get(self, request):
        return render(request, 'admin/vehicle_exit.html')

    def post(self, request):
        return render(request, 'admin/vehicle_exit.html')

class Reports(View):
    def get(self, request):
        return render(request, 'admin/reports.html')
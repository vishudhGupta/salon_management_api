import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_user_apis():
    print("\n=== Testing User APIs ===")
    
    # Create user
    user_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone_number": "1234567890",
        "address": "123 Main St",
        "password": "securepass123"
    }
    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    print("Create User:", response.status_code)
    user = response.json()
    user_id = user["user_id"]
    
    # Get user by ID
    response = requests.get(f"{BASE_URL}/users/{user_id}")
    print("Get User by ID:", response.status_code)
    
    # Get user by email
    response = requests.get(f"{BASE_URL}/users/email/{user_data['email']}")
    print("Get User by Email:", response.status_code)
    
    # Update user
    update_data = {"phone_number": "9876543210"}
    response = requests.put(f"{BASE_URL}/users/{user_id}", json=update_data)
    print("Update User:", response.status_code)
    
    # Get all users
    response = requests.get(f"{BASE_URL}/users/")
    print("Get All Users:", response.status_code)
    
    return user_id

def test_shop_owner_apis(user_id):
    print("\n=== Testing Shop Owner APIs ===")
    
    # Create shop owner
    shop_owner_data = {
        "user_id": user_id,
        "email": "shop@example.com",
        "phone_number": "5555555555",
        "password": "shopsecure123"
    }
    response = requests.post(f"{BASE_URL}/shop-owners/", json=shop_owner_data)
    print("Create Shop Owner:", response.status_code)
    shop_owner = response.json()
    shop_owner_id = shop_owner["shop_owner_id"]
    
    # Get shop owner by ID
    response = requests.get(f"{BASE_URL}/shop-owners/{shop_owner_id}")
    print("Get Shop Owner by ID:", response.status_code)
    
    # Get shop owner by user ID
    response = requests.get(f"{BASE_URL}/shop-owners/user/{user_id}")
    print("Get Shop Owner by User ID:", response.status_code)
    
    # Update shop owner
    update_data = {"phone_number": "6666666666"}
    response = requests.put(f"{BASE_URL}/shop-owners/{shop_owner_id}", json=update_data)
    print("Update Shop Owner:", response.status_code)
    
    # Get all shop owners
    response = requests.get(f"{BASE_URL}/shop-owners/")
    print("Get All Shop Owners:", response.status_code)
    
    return shop_owner_id

def test_salon_apis(shop_owner_id):
    print("\n=== Testing Salon APIs ===")
    
    # Create salon
    salon_data = {
        "shop_owner_id": shop_owner_id,
        "address": "456 Salon St"
    }
    response = requests.post(f"{BASE_URL}/salons/", json=salon_data)
    print("Create Salon:", response.status_code)
    salon = response.json()
    salon_id = salon["salon_id"]
    
    # Get salon by ID
    response = requests.get(f"{BASE_URL}/salons/{salon_id}")
    print("Get Salon by ID:", response.status_code)
    
    # Get salons by owner
    response = requests.get(f"{BASE_URL}/salons/owner/{shop_owner_id}")
    print("Get Salons by Owner:", response.status_code)
    
    # Update salon
    update_data = {"address": "789 New Salon St"}
    response = requests.put(f"{BASE_URL}/salons/{salon_id}", json=update_data)
    print("Update Salon:", response.status_code)
    
    # Get all salons
    response = requests.get(f"{BASE_URL}/salons/")
    print("Get All Salons:", response.status_code)
    
    return salon_id

def test_expert_apis():
    print("\n=== Testing Expert APIs ===")
    
    # Create expert
    expert_data = {
        "name": "Jane Smith",
        "phone": "7777777777",
        "address": "321 Expert Ave",
        "expertise": ["Haircut", "Coloring", "Styling"]
    }
    response = requests.post(f"{BASE_URL}/experts/", json=expert_data)
    print("Create Expert:", response.status_code)
    expert = response.json()
    expert_id = expert["expert_id"]
    
    # Get expert by ID
    response = requests.get(f"{BASE_URL}/experts/{expert_id}")
    print("Get Expert by ID:", response.status_code)
    
    # Get experts by expertise
    response = requests.get(f"{BASE_URL}/experts/expertise/Haircut")
    print("Get Experts by Expertise:", response.status_code)
    
    # Update expert
    update_data = {"phone": "8888888888"}
    response = requests.put(f"{BASE_URL}/experts/{expert_id}", json=update_data)
    print("Update Expert:", response.status_code)
    
    # Get all experts
    response = requests.get(f"{BASE_URL}/experts/")
    print("Get All Experts:", response.status_code)
    
    return expert_id

def test_service_apis():
    print("\n=== Testing Service APIs ===")
    
    # Create service
    service_data = {
        "name": "Haircut",
        "cost": 50.00,
        "duration": 60
    }
    response = requests.post(f"{BASE_URL}/services/", json=service_data)
    print("Create Service:", response.status_code)
    service = response.json()
    service_id = service["service_id"]
    
    # Get service by ID
    response = requests.get(f"{BASE_URL}/services/{service_id}")
    print("Get Service by ID:", response.status_code)
    
    # Get services by price range
    response = requests.get(f"{BASE_URL}/services/price-range/40/60")
    print("Get Services by Price Range:", response.status_code)
    
    # Update service
    update_data = {"cost": 55.00}
    response = requests.put(f"{BASE_URL}/services/{service_id}", json=update_data)
    print("Update Service:", response.status_code)
    
    # Get all services
    response = requests.get(f"{BASE_URL}/services/")
    print("Get All Services:", response.status_code)
    
    return service_id

def test_appointment_apis(user_id, salon_id, service_id):
    print("\n=== Testing Appointment APIs ===")
    
    # Create appointment
    appointment_data = {
        "salon_id": salon_id,
        "user_id": user_id,
        "service_id": service_id,
        "appointment_date": (datetime.now() + timedelta(days=1)).isoformat(),
        "appointment_time": "14:30"
    }
    response = requests.post(f"{BASE_URL}/appointments/", json=appointment_data)
    print("Create Appointment:", response.status_code)
    appointment = response.json()
    appointment_id = appointment["appointment_id"]
    
    # Get appointment by ID
    response = requests.get(f"{BASE_URL}/appointments/{appointment_id}")
    print("Get Appointment by ID:", response.status_code)
    
    # Get user appointments
    response = requests.get(f"{BASE_URL}/appointments/user/{user_id}")
    print("Get User Appointments:", response.status_code)
    
    # Get salon appointments
    response = requests.get(f"{BASE_URL}/appointments/salon/{salon_id}")
    print("Get Salon Appointments:", response.status_code)
    
    # Update appointment
    update_data = {"status": "confirmed"}
    response = requests.put(f"{BASE_URL}/appointments/{appointment_id}", json=update_data)
    print("Update Appointment:", response.status_code)
    
    # Get all appointments
    response = requests.get(f"{BASE_URL}/appointments/")
    print("Get All Appointments:", response.status_code)

def main():
    try:
        # Test all APIs in sequence
        user_id = test_user_apis()
        shop_owner_id = test_shop_owner_apis(user_id)
        salon_id = test_salon_apis(shop_owner_id)
        expert_id = test_expert_apis()
        service_id = test_service_apis()
        test_appointment_apis(user_id, salon_id, service_id)
        
        print("\nAll API tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 
from fastapi import FastAPI, Request, HTTPException
from config.database import Database
from services.booking_service import BookingService
from routes import (
    user_routes,
    shop_owner_routes,
    salon_routes,
    appointment_routes,
    expert_routes,
    service_routes
)
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="Salon Management System")
# Initialize booking_service as None, will be set during startup
booking_service = None

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(user_routes.router, prefix="/api/users", tags=["users"])
app.include_router(shop_owner_routes.router, prefix="/api/shop-owners", tags=["shop-owners"])
app.include_router(salon_routes.router, prefix="/api/salons", tags=["salons"])
app.include_router(appointment_routes.router, prefix="/api/appointments", tags=["appointments"])
app.include_router(expert_routes.router, prefix="/api/experts", tags=["experts"])
app.include_router(service_routes.router, prefix="/api/services", tags=["services"])

@app.on_event("startup")
async def startup_db_client():
    global booking_service
    try:
        await Database.connect_db()
        
        # Initialize BookingService after database connection is established
        booking_service = BookingService()
        
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_db_client():
    try:
        await Database.close_db()
    except Exception as e:
        print(f"Error during shutdown: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "Welcome to Salon Management System API"}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    try:
        form_data = await request.form()
        from_number = form_data.get("From")
        body = form_data.get("Body")

        if not from_number or not body:
            raise HTTPException(status_code=400, detail="Missing From or Body parameters")

        print(f"Received message from {from_number}: {body}")
        
        # Handle the message
        response = await booking_service.handle_incoming_message(from_number, body)
        
        return response
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/appointment-response")
async def handle_appointment_response(request: Request):
    try:
        form_data = await request.form()
        from_number = form_data.get("From")
        message_body = form_data.get("Body")
        
        if not from_number or not message_body:
            raise HTTPException(status_code=400, detail="Missing required parameters")
        
        print(f"Received appointment response webhook - From: {from_number}, Body: {message_body}")
        
        # Handle the appointment response
        await booking_service.handle_appointment_response(from_number, message_body)
        
        print(f"Successfully processed appointment response from {from_number}")
        return {"status": "success"}
    except Exception as e:
        print(f"Error processing appointment response webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

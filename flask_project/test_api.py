"""
Comprehensive End-to-End API Test Suite for AgriNiramaya
Tests all REST endpoints, authentication, CRUD, file uploads, IoT telemetry, and classification.
"""

import os
import io
import json
import unittest
import sys

# Ensure flask_project is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "flask_project")))

from app import app
from database import init_db

class AgriNiramayaApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

    def test_01_health_check(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "online")
        print("[PASS] Health check passed")

    def test_02_register_and_login(self):
        # Register
        reg_payload = {
            "name": "Dr. Anjali Patil",
            "email": "anjali.patil@agri.org",
            "password": "securepassword123",
            "security_question": "What is your favorite crop or plant?",
            "security_answer": "Soybean"
        }
        res = self.client.post("/api/register", json=reg_payload)
        self.assertIn(res.status_code, [201, 400]) # 400 if already exists

        # Login
        login_payload = {
            "email": "anjali.patil@agri.org",
            "password": "securepassword123"
        }
        res = self.client.post("/api/login", json=login_payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("token", data)
        self.user_token = data["token"]
        print("[PASS] Register & Login passed, token:", self.user_token)

        # GET /me with session
        me_res = self.client.get("/api/me")
        me_data = me_res.get_json()
        self.assertTrue(me_data["authenticated"])
        self.assertEqual(me_data["user"]["email"], "anjali.patil@agri.org")
        print("[PASS] Authenticated /me passed")

    def test_03_farm_crud(self):
        # Create Farm
        farm_payload = {
            "name": "Khed Experimental Farm A",
            "location": "Pune Rural Sector",
            "size": 4.5,
            "crop_name": "Tomato",
            "crop_variety": "Abhinav Hybrid",
            "soil_type": "Black Cotton",
            "irrigation_method": "Drip Irrigation",
            "field_info": "North terrace plot with sensor node 01"
        }
        res = self.client.post("/api/farms", json=farm_payload)
        self.assertEqual(res.status_code, 201)
        farm_id = res.get_json()["farm_id"]
        print("[PASS] Farm created with ID:", farm_id)

        # Get Farms
        res = self.client.get("/api/farms")
        self.assertEqual(res.status_code, 200)
        farms = res.get_json()["farms"]
        self.assertGreaterEqual(len(farms), 1)
        print("[PASS] Get Farms returned count:", len(farms))

        # Update Farm
        res = self.client.put(f"/api/farms/{farm_id}", json={
            "name": "Khed Experimental Farm A (Updated)",
            "location": "Pune Rural Sector",
            "size": 5.0,
            "crop_name": "Tomato",
            "crop_variety": "Abhinav Hybrid",
            "soil_type": "Black Cotton",
            "irrigation_method": "Drip Irrigation",
            "field_info": "Added automated solenoid valve"
        })
        self.assertEqual(res.status_code, 200)
        print("[PASS] Farm updated successfully")

    def test_04_leaf_image_upload(self):
        # Create a mock JPEG image bytes
        mock_image = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\xff\xd9")
        data = {
            "crop_name": "Tomato",
            "image": (mock_image, "tomato_early_blight_sample.jpg")
        }
        res = self.client.post("/api/upload-leaf", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 201)
        res_data = res.get_json()
        self.assertTrue(res_data["success"])
        upload_id = res_data["record"]["id"]
        print("[PASS] Leaf uploaded, ID:", upload_id, "Status:", res_data["record"]["status"])

        # Fetch image back
        img_res = self.client.get(f"/api/leaf-image/{upload_id}")
        self.assertEqual(img_res.status_code, 200)
        print("[PASS] Leaf image served successfully via /api/leaf-image/<id>")

    def test_05_soil_telemetry_and_classification(self):
        # 1. Post telemetry
        sensor_payload = {
            "device_id": "ESP32_NODE_TEST_01",
            "moisture": 58.5,
            "temperature": 24.2,
            "ph": 6.8,
            "humidity": 68.0,
            "is_test_data": 0
        }
        res = self.client.post("/api/sensor-data", json=sensor_payload)
        self.assertEqual(res.status_code, 201)
        reading_id = res.get_json()["reading_id"]
        print("[PASS] Soil telemetry posted, reading ID:", reading_id)

        # 2. Get latest soil
        latest_res = self.client.get("/api/latest-soil")
        self.assertEqual(latest_res.status_code, 200)
        latest_data = latest_res.get_json()
        self.assertTrue(latest_data["has_data"])
        self.assertEqual(latest_data["reading"]["moisture"], 58.5)
        print("[PASS] Latest soil returned:", latest_data["reading"]["soil_classification"])

        # 3. Classify soil on-demand
        classify_res = self.client.post("/api/classify-soil", json={"moisture": 15.0, "temperature": 32.0, "ph": 8.8})
        self.assertEqual(classify_res.status_code, 200)
        c_data = classify_res.get_json()["analysis"]
        self.assertIn("Alkaline", c_data["classification"])
        print("[PASS] On-demand Soil Classification:", c_data["classification"])

    def test_06_assistant_and_dashboard_stats(self):
        # Assistant question
        q_res = self.client.post("/api/assistant", json={"message": "How often should I water my tomato crops?"})
        self.assertEqual(q_res.status_code, 200)
        ans = q_res.get_json()["response"]["answer"]
        self.assertIn("Watering Guidelines", ans)
        print("[PASS] Assistant answer matched agronomy rulebook")

        # Dashboard stats
        dash_res = self.client.get("/api/dashboard-stats")
        self.assertEqual(dash_res.status_code, 200)
        stats = dash_res.get_json()["stats"]
        self.assertGreaterEqual(stats["total_farms"], 1)
        self.assertGreaterEqual(stats["total_crops"], 1)
        self.assertGreaterEqual(stats["total_uploads"], 1)
        self.assertGreaterEqual(stats["total_soil_readings"], 1)
        print("[PASS] Authentic Dashboard stats:", stats)

    def test_07_forgot_password_recovery(self):
        # Step 1: get question
        res1 = self.client.post("/api/forgot-password", json={"action": "get_question", "email": "anjali.patil@agri.org"})
        self.assertEqual(res1.status_code, 200)
        self.assertIn("security_question", res1.get_json())
        print("[PASS] Retrieved recovery question:", res1.get_json()["security_question"])

        # Step 2: reset
        res2 = self.client.post("/api/forgot-password", json={
            "action": "reset",
            "email": "anjali.patil@agri.org",
            "security_answer": "Soybean",
            "new_password": "brandnewpassword456"
        })
        self.assertEqual(res2.status_code, 200)
        print("[PASS] Password reset verified successfully")

if __name__ == "__main__":
    unittest.main()

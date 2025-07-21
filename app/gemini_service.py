from google import genai
import os

class GeminiService:
    def __init__(self):
        self.client = genai.Client()

    def analyze_health_summary(self, health_summary, prescriptions):
        try:
            prompt = f"""
            Analyze this patient health summary and medication history to provide a concise medical summary for the doctor:
            
            Health Summary:
            {health_summary}
            
            Current Prescriptions:
            {prescriptions}
            
            Please provide:
            1. Key health concerns
            2. Medication adherence analysis
            3. Potential interactions or concerns
            4. General health assessment
            
            Keep the response professional and concise (under 200 words).
            """

            # model = self.client.get_model(f"models/gemini-1.5-flash") 
            # response = model.generate_content(prompt)

            # return response.text
            
            response = self.client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[{"role": "user", "parts": [{"text": prompt}]}]  
            )
            return response.text
        except Exception as e:
            print(f"Error with Gemini API: {e}")
            return "Could not generate analysis at this time."
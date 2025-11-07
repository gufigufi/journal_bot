import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self.service = None
        self._init_service()
    
    def _init_service(self):
        try:
            if not os.path.exists(self.credentials_path):
                logger.warning(f"Credentials file not found: {self.credentials_path}")
                return
            
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Google Sheets service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {e}")
    
    def get_sheet_names(self, spreadsheet_id: str) -> List[str]:
        if not self.service:
            return []
        
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheets = spreadsheet.get('sheets', [])
            return [sheet['properties']['title'] for sheet in sheets]
        except Exception as e:
            logger.error(f"Failed to get sheet names: {e}")
            return []
    
    def get_student_grades(
        self, 
        spreadsheet_id: str, 
        sheet_name: str, 
        student_name: str
    ) -> Optional[Dict[str, Any]]:
        if not self.service:
            return None
        
        try:
            range_name = f"{sheet_name}!A1:Z100"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if len(values) < 4:
                return None
            
            subject_name = values[0][0] if len(values[0]) > 0 else sheet_name
            
            lesson_types = values[1][3:] if len(values[1]) > 3 else []
            lesson_dates = values[2][3:] if len(values[2]) > 3 else []
            
            student_row = None
            for row in values[3:]:
                if len(row) > 2 and row[2].strip() == student_name.strip():
                    student_row = row
                    break
            
            if not student_row:
                return None
            
            grades = student_row[3:] if len(student_row) > 3 else []
            
            grades_data = []
            for i, grade in enumerate(grades):
                lesson_type = lesson_types[i] if i < len(lesson_types) else ""
                lesson_date = lesson_dates[i] if i < len(lesson_dates) else ""
                
                if not lesson_type and not lesson_date and not grade:
                    continue
                
                display_grade = grade if grade else "пусто"
                
                grades_data.append({
                    'lesson_type': lesson_type,
                    'lesson_date': lesson_date,
                    'grade': display_grade
                })
            
            return {
                'subject': subject_name,
                'student_name': student_name,
                'grades': grades_data
            }
        
        except Exception as e:
            logger.error(f"Failed to get student grades: {e}")
            return None

import aiosqlite
import os
from typing import Optional, List, Dict, Any
from datetime import datetime


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
    
    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            with open('schema.sql', 'r', encoding='utf-8') as f:
                schema = f.read()
            await db.executescript(schema)
            await db.commit()
    
    async def get_all_groups(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM groups ORDER BY name") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_group_by_spreadsheet_id(self, spreadsheet_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM groups WHERE spreadsheet_id = ?", 
                (spreadsheet_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def find_student(self, full_name: str, group_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM students WHERE full_name = ? AND group_id = ?",
                (full_name, group_id)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def update_student_chat_id(self, student_id: int, role: str, chat_id: str) -> bool:
        field_map = {
            'студент': 'student_chat_id',
            'батько': 'father_chat_id',
            'мати': 'mother_chat_id'
        }
        
        field = field_map.get(role)
        if not field:
            return False
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE students SET {field} = ? WHERE id = ?",
                (chat_id, student_id)
            )
            await db.commit()
            return True
    
    async def create_grade_event(
        self,
        group_id: int,
        student_full_name: str,
        subject: str,
        lesson_type: Optional[str],
        lesson_date: Optional[str],
        column_letter: Optional[str],
        row_index: Optional[int],
        old_value: Optional[str],
        new_value: Optional[str],
        gsheet_edit_timestamp: Optional[str]
    ) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO grade_events 
                (group_id, student_full_name, subject, lesson_type, lesson_date, 
                column_letter, row_index, old_value, new_value, gsheet_edit_timestamp, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (group_id, student_full_name, subject, lesson_type, lesson_date,
                 column_letter, row_index, old_value, new_value, gsheet_edit_timestamp)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def get_unprocessed_events(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM grade_events WHERE processed = 0 ORDER BY created_at"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def mark_event_processed(self, event_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE grade_events SET processed = 1 WHERE id = ?",
                (event_id,)
            )
            await db.commit()
    
    async def get_student_by_id(self, student_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM students WHERE id = ?",
                (student_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def add_group(self, name: str, spreadsheet_id: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO groups (name, spreadsheet_id) VALUES (?, ?)",
                (name, spreadsheet_id)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def add_student(self, full_name: str, group_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO students (full_name, group_id) VALUES (?, ?)",
                (full_name, group_id)
            )
            await db.commit()
            return cursor.lastrowid

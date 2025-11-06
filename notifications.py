import logging
from typing import Dict, Any, Optional
from database import Database
from bot import TelegramBot


logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, database: Database, telegram_bot: TelegramBot):
        self.db = database
        self.bot = telegram_bot
    
    def format_grade_message(self, event: Dict[str, Any]) -> str:
        lines = []
        
        subject = event.get('subject', 'Невідомий предмет')
        lines.append(f"Предмет: {subject}")
        
        lesson_date = event.get('lesson_date')
        if lesson_date:
            lines.append(f"Дата: {lesson_date}")
        
        lesson_type = event.get('lesson_type')
        if lesson_type:
            lines.append(f"Тип: {lesson_type}")
        
        old_value = event.get('old_value')
        new_value = event.get('new_value')
        
        if new_value is None or new_value == '':
            lines.append("Оцінка видалена")
        elif old_value and old_value != new_value:
            lines.append(f"Було: {old_value} → Стало: {new_value}")
        else:
            lines.append(f"Оцінка: {new_value}")
        
        return '\n'.join(lines)
    
    async def process_grade_event(self, event: Dict[str, Any]) -> bool:
        try:
            student_full_name = event['student_full_name']
            group_id = event['group_id']
            
            student = await self.db.find_student(student_full_name, group_id)
            
            if not student:
                logger.warning(
                    f"Student {student_full_name} not found in group {group_id}"
                )
                return False
            
            message = self.format_grade_message(event)
            
            sent_count = 0
            
            if student.get('student_chat_id'):
                if await self.bot.send_notification(student['student_chat_id'], message):
                    sent_count += 1
            
            if student.get('father_chat_id'):
                if await self.bot.send_notification(student['father_chat_id'], message):
                    sent_count += 1
            
            if student.get('mother_chat_id'):
                if await self.bot.send_notification(student['mother_chat_id'], message):
                    sent_count += 1
            
            logger.info(
                f"Sent {sent_count} notifications for event {event['id']}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing grade event {event.get('id')}: {e}")
            return False
    
    async def process_pending_events(self):
        events = await self.db.get_unprocessed_events()
        
        logger.info(f"Processing {len(events)} pending events")
        
        for event in events:
            success = await self.process_grade_event(event)
            
            if success:
                await self.db.mark_event_processed(event['id'])

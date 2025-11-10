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
        """Форматирует сообщение с эмодзи и красивым оформлением"""
        lines = []
        
        # Заголовок с эмодзи
        lines.append("📚 *Нова оцінка!*\n")
        
        subject = event.get('subject', 'Невідомий предмет')
        lines.append(f"📖 Предмет: *{subject}*")
        
        lesson_date = event.get('lesson_date')
        if lesson_date:
            lines.append(f"📅 Дата: {lesson_date}")
        
        lesson_type = event.get('lesson_type')
        if lesson_type:
            lines.append(f"📝 Тип заняття: {lesson_type}")
        
        old_value = event.get('old_value', '').strip()
        new_value = event.get('new_value', '').strip()
        
        # Определяем эмодзи в зависимости от оценки
        grade_emoji = self._get_grade_emoji(new_value)
        
        if not new_value:
            lines.append(f"\n❌ Оцінку видалено")
        elif old_value and old_value != new_value:
            lines.append(f"\n{grade_emoji} Було: *{old_value}* → Стало: *{new_value}*")
        else:
            lines.append(f"\n{grade_emoji} Оцінка: *{new_value}*")
        
        return '\n'.join(lines)
    
    def _get_grade_emoji(self, grade: str) -> str:
        """Возвращает эмодзи в зависимости от оценки"""
        if not grade:
            return "❓"
        
        try:
            grade_num = int(grade)
            if grade_num >= 10:
                return "🌟"
            elif grade_num >= 8:
                return "✅"
            elif grade_num >= 6:
                return "📊"
            else:
                return "⚠️"
        except:
            # Если это не число (например, "н/а", "+" и т.д.)
            return "📌"
    
    async def process_grade_event(self, event: Dict[str, Any]) -> bool:
        """Обрабатывает событие изменения оценки и отправляет уведомления"""
        try:
            event_id = event.get('id', 'unknown')
            student_full_name = event.get('student_full_name', '')
            group_id = event.get('group_id')
            
            logger.info(f"=== Processing event {event_id} ===")
            logger.info(f"Student name: '{student_full_name}'")
            logger.info(f"Group ID: {group_id}")
            logger.info(f"Subject: {event.get('subject')}")
            logger.info(f"Old value: '{event.get('old_value')}'")
            logger.info(f"New value: '{event.get('new_value')}'")
            
            # Ищем студента в БД
            student = await self.db.find_student(student_full_name, group_id)
            
            if not student:
                logger.error(
                    f"❌ Student '{student_full_name}' NOT FOUND in group {group_id}"
                )
                # Можно попробовать найти похожих студентов
                await self._log_similar_students(student_full_name, group_id)
                return False
            
            logger.info(f"✅ Student found: ID={student['id']}")
            logger.info(f"Student chat_id: {student.get('student_chat_id')}")
            logger.info(f"Father chat_id: {student.get('father_chat_id')}")
            logger.info(f"Mother chat_id: {student.get('mother_chat_id')}")
            
            # Формируем сообщение
            message = self.format_grade_message(event)
            logger.info(f"Message formatted:\n{message}")
            
            sent_count = 0
            failed_count = 0
            
            # Отправляем студенту
            if student.get('student_chat_id'):
                logger.info(f"Sending to student chat_id: {student['student_chat_id']}")
                if await self.bot.send_notification(student['student_chat_id'], message):
                    sent_count += 1
                    logger.info("✅ Sent to student")
                else:
                    failed_count += 1
                    logger.error("❌ Failed to send to student")
            else:
                logger.warning("⚠️ Student has no chat_id (not registered in bot)")
            
            # Отправляем отцу
            if student.get('father_chat_id'):
                logger.info(f"Sending to father chat_id: {student['father_chat_id']}")
                if await self.bot.send_notification(student['father_chat_id'], message):
                    sent_count += 1
                    logger.info("✅ Sent to father")
                else:
                    failed_count += 1
                    logger.error("❌ Failed to send to father")
            
            # Отправляем матери
            if student.get('mother_chat_id'):
                logger.info(f"Sending to mother chat_id: {student['mother_chat_id']}")
                if await self.bot.send_notification(student['mother_chat_id'], message):
                    sent_count += 1
                    logger.info("✅ Sent to mother")
                else:
                    failed_count += 1
                    logger.error("❌ Failed to send to mother")
            
            logger.info(
                f"📊 Event {event_id} summary: "
                f"sent={sent_count}, failed={failed_count}"
            )
            
            # Событие считается успешным если хотя бы одно сообщение отправлено
            return sent_count > 0
            
        except Exception as e:
            logger.error(
                f"❌ Exception in process_grade_event {event.get('id')}: {e}", 
                exc_info=True
            )
            return False
    
    async def _log_similar_students(self, student_name: str, group_id: int):
        """Логирует похожих студентов для отладки"""
        try:
            # Получаем всех студентов группы
            async with self.db.db_path as conn:
                cursor = await conn.execute(
                    "SELECT full_name FROM students WHERE group_id = ?",
                    (group_id,)
                )
                students = await cursor.fetchall()
                
                if students:
                    logger.info(f"Students in group {group_id}:")
                    for s in students:
                        logger.info(f"  - '{s[0]}'")
                else:
                    logger.warning(f"No students found in group {group_id}")
        except Exception as e:
            logger.error(f"Error logging similar students: {e}")
    
    async def process_pending_events(self):
        """Обрабатывает все необработанные события"""
        try:
            events = await self.db.get_unprocessed_events()
            
            logger.info(f"📋 Found {len(events)} pending events to process")
            
            if not events:
                logger.info("No pending events")
                return
            
            for event in events:
                logger.info(f"\n{'='*50}")
                success = await self.process_grade_event(event)
                
                if success:
                    await self.db.mark_event_processed(event['id'])
                    logger.info(f"✅ Event {event['id']} marked as processed")
                else:
                    logger.warning(f"⚠️ Event {event['id']} processing failed, will retry later")
                    # НЕ помечаем как обработанное, чтобы попробовать еще раз
            
            logger.info(f"{'='*50}\n")
            
        except Exception as e:
            logger.error(f"Error in process_pending_events: {e}", exc_info=True)
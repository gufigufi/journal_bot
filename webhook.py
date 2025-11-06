from aiohttp import web
import logging
import os
from typing import Optional
from database import Database
from notifications import NotificationService


logger = logging.getLogger(__name__)


class WebhookHandler:
    def __init__(self, database: Database, notification_service: NotificationService, secret: str):
        self.db = database
        self.notification_service = notification_service
        self.secret = secret
    
    def verify_secret(self, request: web.Request) -> bool:
        token = request.headers.get('X-GAS-Token')
        return token == self.secret
    
    async def handle_webhook(self, request: web.Request) -> web.Response:
        if not self.verify_secret(request):
            logger.warning("Unauthorized webhook request")
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        try:
            data = await request.json()
            
            spreadsheet_id = data.get('spreadsheetId')
            sheet_name = data.get('sheetName')
            student_name = data.get('studentName')
            subject = data.get('subject')
            lesson_type = data.get('lessonType')
            lesson_date = data.get('lessonDate')
            column_letter = data.get('columnLetter')
            row_index = data.get('rowIndex')
            old_value = data.get('oldValue')
            new_value = data.get('newValue')
            timestamp = data.get('timestamp')
            
            if not all([spreadsheet_id, sheet_name, student_name, subject]):
                return web.json_response(
                    {'error': 'Missing required fields'}, 
                    status=400
                )
            
            group = await self.db.get_group_by_spreadsheet_id(spreadsheet_id)
            
            if not group:
                logger.warning(f"Group not found for spreadsheet {spreadsheet_id}")
                return web.json_response(
                    {'error': 'Group not found'}, 
                    status=404
                )
            
            event_id = await self.db.create_grade_event(
                group_id=group['id'],
                student_full_name=student_name,
                subject=subject,
                lesson_type=lesson_type,
                lesson_date=lesson_date,
                column_letter=column_letter,
                row_index=row_index,
                old_value=old_value,
                new_value=new_value,
                gsheet_edit_timestamp=timestamp
            )
            
            logger.info(f"Created grade event {event_id}")
            
            await self.notification_service.process_pending_events()
            
            return web.json_response({'status': 'ok', 'event_id': event_id})
            
        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            return web.json_response(
                {'error': 'Internal server error'}, 
                status=500
            )


async def create_webhook_app(database: Database, notification_service: NotificationService) -> web.Application:
    secret = os.getenv('APPS_SCRIPT_WEBHOOK_SECRET', 'supersecret')
    handler = WebhookHandler(database, notification_service, secret)
    
    app = web.Application()
    app.router.add_post('/webhook/grades', handler.handle_webhook)
    
    return app

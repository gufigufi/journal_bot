from aiohttp import web
import aiohttp_session
from aiohttp_session import setup, get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
import aiohttp_jinja2
import jinja2
import hashlib
import logging
import os
from database import Database
from google_sheets import GoogleSheetsService

logger = logging.getLogger(__name__)


async def login_page(request):
    session = await get_session(request)
    if 'student_id' in session:
        return web.HTTPFound('/dashboard')
    
    return aiohttp_jinja2.render_template('login.html', request, {})


async def login_handler(request):
    data = await request.post()
    login = data.get('login', '').strip()
    password = data.get('password', '').strip()
    
    if not login or not password:
        return aiohttp_jinja2.render_template('login.html', request, {
            'error': 'Будь ласка, заповніть всі поля'
        })
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    db = request.app['db']
    student = await db.verify_web_credentials(login, password_hash)
    
    if not student:
        return aiohttp_jinja2.render_template('login.html', request, {
            'error': 'Невірний логін або пароль'
        })
    
    session = await get_session(request)
    session['student_id'] = student['id']
    session['student_name'] = student['full_name']
    session['group_id'] = student['group_id']
    
    return web.HTTPFound('/dashboard')


async def logout_handler(request):
    session = await get_session(request)
    session.clear()
    return web.HTTPFound('/')


async def dashboard(request):
    session = await get_session(request)
    
    if 'student_id' not in session:
        return web.HTTPFound('/')
    
    db = request.app['db']
    group = await db.get_group_by_id(session['group_id'])
    
    if not group:
        return aiohttp_jinja2.render_template('dashboard.html', request, {
            'student_name': session['student_name'],
            'error': 'Група не знайдена'
        })
    
    sheets_service = request.app['sheets_service']
    sheet_names = sheets_service.get_sheet_names(group['spreadsheet_id'])
    
    subjects = [name for name in sheet_names if name.lower() not in ['список', 'список групи']]
    
    return aiohttp_jinja2.render_template('dashboard.html', request, {
        'student_name': session['student_name'],
        'subjects': subjects
    })


async def view_grades(request):
    session = await get_session(request)
    
    if 'student_id' not in session:
        return web.HTTPFound('/')
    
    subject = request.match_info.get('subject')
    
    try:
        db = request.app['db']
        group = await db.get_group_by_id(session['group_id'])
        
        if not group:
            return aiohttp_jinja2.render_template('grades.html', request, {
                'student_name': session['student_name'],
                'subject': subject,
                'error': 'Група не знайдена'
            })
        
        sheets_service = request.app['sheets_service']
        grades_data = sheets_service.get_student_grades(
            group['spreadsheet_id'],
            subject,
            session['student_name']
        )
        
        if not grades_data:
            return aiohttp_jinja2.render_template('grades.html', request, {
                'student_name': session['student_name'],
                'subject': subject,
                'error': 'Оцінки не знайдено'
            })
        
        return aiohttp_jinja2.render_template('grades.html', request, {
            'student_name': session['student_name'],
            'subject': grades_data['subject'],
            'grades': grades_data['grades']
        })
    except Exception as e:
        logger.error(f"Error in view_grades: {e}", exc_info=True)
        return aiohttp_jinja2.render_template('grades.html', request, {
            'student_name': session.get('student_name', 'Невідомий'),
            'subject': subject,
            'error': f'Помилка при отриманні оцінок: {str(e)}'
        })


async def create_web_app(db: Database, sheets_service: GoogleSheetsService):
    app = web.Application()
    
    secret_key = os.getenv('WEB_SECRET_KEY')
    if not secret_key:
        secret_key = fernet.Fernet.generate_key().decode()
    
    setup(app, EncryptedCookieStorage(secret_key))
    
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader('templates')
    )
    
    app['db'] = db
    app['sheets_service'] = sheets_service
    
    app.router.add_get('/', login_page)
    app.router.add_post('/login', login_handler)
    app.router.add_get('/logout', logout_handler)
    app.router.add_get('/dashboard', dashboard)
    app.router.add_get('/grades/{subject}', view_grades)
    
    app.router.add_static('/static', 'static')
    
    return app

async def view_grades(request):
    session = await get_session(request)
    
    if 'student_id' not in session:
        return web.HTTPFound('/')
    
    from urllib.parse import unquote
    subject = unquote(request.match_info.get('subject'))
    
    try:
        db = request.app['db']
        group = await db.get_group_by_id(session['group_id'])
        
        if not group:
            return aiohttp_jinja2.render_template('grades.html', request, {
                'student_name': session['student_name'],
                'subject': subject,
                'error': 'Група не знайдена'
            })
        
        sheets_service = request.app['sheets_service']
        grades_data = sheets_service.get_student_grades(
            group['spreadsheet_id'],
            subject,
            session['student_name']
        )
        
        if not grades_data:
            return aiohttp_jinja2.render_template('grades.html', request, {
                'student_name': session['student_name'],
                'subject': subject,
                'error': 'Оцінки не знайдено'
            })
        
        return aiohttp_jinja2.render_template('grades.html', request, {
            'student_name': session['student_name'],
            'subject': grades_data['subject'],
            'grades': grades_data['grades']
        })
    except Exception as e:
        logger.error(f"Error in view_grades: {e}", exc_info=True)
        return aiohttp_jinja2.render_template('grades.html', request, {
            'student_name': session.get('student_name', 'Невідомий'),
            'subject': subject,
            'error': f'Помилка при отриманні оцінок: {str(e)}'
        })

from aiohttp import web
import aiohttp_session
from aiohttp_session import setup, get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
import aiohttp_jinja2
import jinja2
import hashlib
import logging
import os
import re
from database import Database
from google_sheets import GoogleSheetsService

logger = logging.getLogger(__name__)


def transliterate(text):
    translit_dict = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd', 'е': 'e', 'є': 'ye',
        'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'yi', 'й': 'y', 'к': 'k', 'л': 'l',
        'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ь': '', 'ю': 'yu',
        'я': 'ya', 'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'H', 'Ґ': 'G', 'Д': 'D', 'Е': 'E',
        'Є': 'Ye', 'Ж': 'Zh', 'З': 'Z', 'И': 'Y', 'І': 'I', 'Ї': 'Yi', 'Й': 'Y', 'К': 'K',
        'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
        'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ь': '',
        'Ю': 'Yu', 'Я': 'Ya', ' ': '-', '(': '', ')': '', '.': '', ',': '', '\'': '', '"': ''
    }
    result = ''
    for char in text:
        result += translit_dict.get(char, char)
    result = re.sub(r'-+', '-', result)
    result = result.strip('-')
    return result.lower()

async def dashboard(request):
    session = await get_session(request)
    
    if 'student_id' not in session:
        return web.HTTPFound('/')
    
    db = request.app['db']
    group = await db.get_group_by_id(session['group_id'])
    
    if not group:
        return aiohttp_jinja2.render_template('dashboard.html', request, {
            'student_name': session['student_name'],
            'error': 'Група не знайдена'
        })
    
    sheets_service = request.app['sheets_service']
    sheet_names = sheets_service.get_sheet_names(group['spreadsheet_id'])
    
    filtered_names = [name for name in sheet_names if name.lower() not in ['список', 'список групи']]
    
    subjects = []
    subject_mapping = {}
    for name in filtered_names:
        slug = transliterate(name)
        subjects.append({'name': name, 'slug': slug})
        subject_mapping[slug] = name
    
    session['subject_mapping'] = subject_mapping
    
    return aiohttp_jinja2.render_template('dashboard.html', request, {
        'student_name': session['student_name'],
        'subjects': subjects
    })

async def view_grades(request):
    session = await get_session(request)
    
    if 'student_id' not in session:
        return web.HTTPFound('/')
    
    slug = request.match_info.get('subject')
    subject_mapping = session.get('subject_mapping', {})
    subject = subject_mapping.get(slug, slug)
    
    try:
        db = request.app['db']
        group = await db.get_group_by_id(session['group_id'])
        
        if not group:
            return aiohttp_jinja2.render_template('grades.html', request, {
                'student_name': session['student_name'],
                'subject': subject,
                'error': 'Група не знайдена'
            })
        
        sheets_service = request.app['sheets_service']
        grades_data = sheets_service.get_student_grades(
            group['spreadsheet_id'],
            subject,
            session['student_name']
        )
        
        if not grades_data:
            return aiohttp_jinja2.render_template('grades.html', request, {
                'student_name': session['student_name'],
                'subject': subject,
                'error': 'Оцінки не знайдено'
            })
        
        return aiohttp_jinja2.render_template('grades.html', request, {
            'student_name': session['student_name'],
            'subject': grades_data['subject'],
            'grades': grades_data['grades']
        })
    except Exception as e:
        logger.error(f"Error in view_grades: {e}", exc_info=True)
        return aiohttp_jinja2.render_template('grades.html', request, {
            'student_name': session.get('student_name', 'Невідомий'),
            'subject': subject,
            'error': f'Помилка при отриманні оцінок: {str(e)}'
        })

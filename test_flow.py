import asyncio
import aiosqlite
from database import Database

async def test_complete_flow():
    """Тестирует всю цепочку: БД → Студенты → События → Уведомления"""
    
    db_path = './data/grades.db'
    db = Database(db_path)
    
    print("=" * 60)
    print("ДИАГНОСТИКА СИСТЕМЫ УВЕДОМЛЕНИЙ")
    print("=" * 60)
    
    # ===== 1. ПРОВЕРКА ГРУПП =====
    print("\n📁 1. ПРОВЕРКА ГРУПП В БД:")
    groups = await db.get_all_groups()
    if groups:
        for group in groups:
            print(f"  ✅ ID: {group['id']}, Название: '{group['name']}'")
            print(f"     Spreadsheet ID: {group['spreadsheet_id']}")
    else:
        print("  ❌ ОШИБКА: Нет групп в базе данных!")
        print("     Нужно добавить группу через веб-интерфейс или SQL")
        return
    
    # ===== 2. ПРОВЕРКА СТУДЕНТОВ =====
    print("\n👥 2. ПРОВЕРКА СТУДЕНТОВ:")
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("""
            SELECT s.id, s.full_name, s.group_id, g.name as group_name,
                   s.student_chat_id, s.father_chat_id, s.mother_chat_id
            FROM students s
            JOIN groups g ON s.group_id = g.id
            ORDER BY g.name, s.full_name
        """)
        students = await cursor.fetchall()
        
        if not students:
            print("  ❌ ОШИБКА: Нет студентов в базе данных!")
            print("     Студенты должны добавляться при регистрации в боте")
            return
        
        students_with_chat = 0
        students_without_chat = 0
        
        for student in students:
            has_chat = bool(
                student['student_chat_id'] or 
                student['father_chat_id'] or 
                student['mother_chat_id']
            )
            
            if has_chat:
                students_with_chat += 1
                print(f"  ✅ {student['full_name']} (группа: {student['group_name']})")
                if student['student_chat_id']:
                    print(f"     └─ Студент: {student['student_chat_id']}")
                if student['father_chat_id']:
                    print(f"     └─ Отец: {student['father_chat_id']}")
                if student['mother_chat_id']:
                    print(f"     └─ Мать: {student['mother_chat_id']}")
            else:
                students_without_chat += 1
                print(f"  ⚠️  {student['full_name']} (группа: {student['group_name']})")
                print(f"     └─ НЕ ЗАРЕГИСТРИРОВАН В БОТЕ!")
        
        print(f"\n  📊 Итого:")
        print(f"     Зарегистрировано в боте: {students_with_chat}")
        print(f"     Не зарегистрировано: {students_without_chat}")
    
    # ===== 3. ПРОВЕРКА СОБЫТИЙ =====
    print("\n📬 3. ПРОВЕРКА СОБЫТИЙ ОЦЕНОК:")
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        
        # Необработанные события
        cursor = await conn.execute("""
            SELECT * FROM grade_events 
            WHERE processed = 0 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        pending = await cursor.fetchall()
        
        # Обработанные события
        cursor = await conn.execute("""
            SELECT COUNT(*) as count FROM grade_events WHERE processed = 1
        """)
        processed_count = (await cursor.fetchone())['count']
        
        # Всего событий
        cursor = await conn.execute("SELECT COUNT(*) as count FROM grade_events")
        total_count = (await cursor.fetchone())['count']
        
        print(f"  📊 Всего событий: {total_count}")
        print(f"  ✅ Обработано: {processed_count}")
        print(f"  ⏳ Ожидает обработки: {len(pending)}")
        
        if pending:
            print("\n  📋 Необработанные события:")
            for event in pending:
                print(f"\n  Event ID: {event['id']}")
                print(f"    Студент: {event['student_full_name']}")
                print(f"    Предмет: {event['subject']}")
                print(f"    Было: '{event['old_value']}' → Стало: '{event['new_value']}'")
                print(f"    Создано: {event['created_at']}")
                
                # Проверяем есть ли такой студент
                cursor2 = await conn.execute("""
                    SELECT id, full_name, student_chat_id, father_chat_id, mother_chat_id
                    FROM students 
                    WHERE full_name = ? AND group_id = ?
                """, (event['student_full_name'], event['group_id']))
                student = await cursor2.fetchone()
                
                if student:
                    has_recipients = bool(
                        student['student_chat_id'] or 
                        student['father_chat_id'] or 
                        student['mother_chat_id']
                    )
                    if has_recipients:
                        print(f"    ✅ Студент найден, есть получатели")
                    else:
                        print(f"    ⚠️  Студент найден, но НЕ зарегистрирован в боте!")
                else:
                    print(f"    ❌ СТУДЕНТ НЕ НАЙДЕН В БД!")
                    print(f"       Имя в событии: '{event['student_full_name']}'")
                    
                    # Ищем похожих
                    cursor3 = await conn.execute("""
                        SELECT full_name FROM students WHERE group_id = ?
                    """, (event['group_id'],))
                    similar = await cursor3.fetchall()
                    if similar:
                        print(f"       Студенты в группе:")
                        for s in similar[:5]:
                            print(f"         - '{s['full_name']}'")
    
    # ===== 4. ТЕСТ ОТПРАВКИ УВЕДОМЛЕНИЯ =====
    print("\n" + "=" * 60)
    print("🧪 4. СИМУЛЯЦИЯ ОТПРАВКИ УВЕДОМЛЕНИЯ")
    print("=" * 60)
    
    if pending:
        test_event = dict(pending[0])
        print(f"\nИспользуем первое необработанное событие (ID: {test_event['id']})")
        print(f"Студент: {test_event['student_full_name']}")
        
        student = await db.find_student(
            test_event['student_full_name'], 
            test_event['group_id']
        )
        
        if student:
            print(f"✅ Студент найден в БД")
            
            recipients = []
            if student.get('student_chat_id'):
                recipients.append(f"Студент ({student['student_chat_id']})")
            if student.get('father_chat_id'):
                recipients.append(f"Отец ({student['father_chat_id']})")
            if student.get('mother_chat_id'):
                recipients.append(f"Мать ({student['mother_chat_id']})")
            
            if recipients:
                print(f"📨 Уведомление будет отправлено:")
                for r in recipients:
                    print(f"   └─ {r}")
                
                # Формируем сообщение
                message_lines = ["📚 *Нова оцінка!*\n"]
                message_lines.append(f"📖 Предмет: *{test_event['subject']}*")
                if test_event['lesson_date']:
                    message_lines.append(f"📅 Дата: {test_event['lesson_date']}")
                if test_event['lesson_type']:
                    message_lines.append(f"📝 Тип: {test_event['lesson_type']}")
                
                old = test_event.get('old_value', '').strip()
                new = test_event.get('new_value', '').strip()
                if old and old != new:
                    message_lines.append(f"\n✅ Було: *{old}* → Стало: *{new}*")
                else:
                    message_lines.append(f"\n✅ Оцінка: *{new}*")
                
                message = '\n'.join(message_lines)
                print(f"\n📄 Текст сообщения:")
                print("─" * 40)
                print(message)
                print("─" * 40)
            else:
                print("❌ У студента нет зарегистрированных получателей!")
        else:
            print(f"❌ Студент НЕ найден в БД")
    else:
        print("\n⚠️  Нет необработанных событий для теста")
    
    # ===== 5. РЕКОМЕНДАЦИИ =====
    print("\n" + "=" * 60)
    print("💡 РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    
    if students_without_chat > 0:
        print(f"\n⚠️  {students_without_chat} студентов не зарегистрированы в боте")
        print("   Они должны:")
        print("   1. Написать боту /start")
        print("   2. Выбрать роль (студент/батько/мати)")
        print("   3. Выбрать группу")
        print("   4. Ввести ПІБ ТОЧНО как в Google Sheets")
    
    if pending:
        print(f"\n📬 Есть {len(pending)} необработанных событий")
        print("   Проверьте что:")
        print("   1. Бот запущен и работает")
        print("   2. NotificationService.process_pending_events() вызывается")
        print("   3. Нет ошибок в логах при отправке")
    
    print("\n✅ Диагностика завершена!")
    print("=" * 60)

if __name__ == '__main__':
    asyncio.run(test_complete_flow())
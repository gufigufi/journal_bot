import asyncio
import sys
from database import Database


async def add_sample_data():
    db = Database('./data/grades.db')
    await db.init_db()
    
    print("Додавання тестових даних...")
    
    group_id = await db.add_group(
        name="П-21",
        spreadsheet_id="1Npfelri9lQACDiq5Jy-eIG1DC9SOF9gtHH0BaRcN1ek"
    )
    print(f"Створено групу ІП-21 (ID: {group_id})")
    
    students = [
        "Бологан Данііл Максимович"
    ]
    
    for student_name in students:
        student_id = await db.add_student(student_name, group_id)
        print(f"Додано студента: {student_name} (ID: {student_id})")
    
    print("\nГотово! Тепер замініть 'your_spreadsheet_id_here' на реальний ID таблиці.")


if __name__ == '__main__':
    asyncio.run(add_sample_data())

// ВАЖНО: URL должен совпадать с маршрутом в webhook.py
const WEBHOOK_URL = "https://jbot.khpcc.com/webhook/grades";
const WEBHOOK_SECRET = "a8f3k2m9p1q7w4e6r5t8y2u3i0o9p8l7"; // Тот же что в .env APPS_SCRIPT_WEBHOOK_SECRET

/**
 * Устанавливаемый триггер для отслеживания изменений
 * ВАЖНО: Функция должна называться НЕ onEdit!
 */
function onEditInstallable(e) {
  try {
    Logger.log("=== Trigger fired ===");

    // Проверка что событие существует
    if (!e) {
      Logger.log("ERROR: Event object is null");
      return;
    }

    const sheet = e.source.getActiveSheet();
    const sheetName = sheet.getName();
    const spreadsheetId = e.source.getId();

    Logger.log("Spreadsheet ID: " + spreadsheetId);
    Logger.log("Sheet name: " + sheetName);

    // Игнорируем первый лист (реестр студентов)
    const firstSheet = e.source.getSheets()[0];
    if (sheet.getSheetId() === firstSheet.getSheetId()) {
      Logger.log("Edit in first sheet (roster), ignoring");
      return;
    }

    const range = e.range;
    const row = range.getRow();
    const column = range.getColumn();

    Logger.log("Row: " + row + ", Column: " + column);

    // Игнорируем редактирование заголовков (строки 1-3) и имён студентов (колонки A-C)
    if (row <= 3 || column < 4) {
      Logger.log("Edit outside grade area (headers or names), ignoring");
      return;
    }

    // Получаем название предмета из A1
    const subject = sheet.getRange("A1").getValue() || sheetName;

    // Получаем тип занятия из строки 2
    const lessonType = sheet.getRange(2, column).getValue() || "";

    // Получаем дату из строки 3
    const lessonDate = sheet.getRange(3, column).getValue() || "";

    // Получаем имя студента из колонки C текущей строки
    const studentName = sheet.getRange(row, 3).getValue();

    if (!studentName) {
      Logger.log("No student name in row " + row + ", ignoring");
      return;
    }

    Logger.log("Student: " + studentName);
    Logger.log("Subject: " + subject);

    // Получаем старое и новое значение
    const oldValue = e.oldValue || "";
    const newValue = e.value || "";

    Logger.log('Old value: "' + oldValue + '"');
    Logger.log('New value: "' + newValue + '"');

    const columnLetter = columnToLetter(column);

    // Формируем payload
    const payload = {
      spreadsheetId: spreadsheetId,
      sheetName: sheetName,
      subject: subject,
      studentName: studentName,
      lessonType: lessonType,
      lessonDate: lessonDate,
      columnLetter: columnLetter,
      rowIndex: row,
      oldValue: oldValue,
      newValue: newValue,
      timestamp: new Date().toISOString(),
    };

    Logger.log("Payload: " + JSON.stringify(payload));

    // Отправляем webhook
    const options = {
      method: "post",
      contentType: "application/json",
      headers: {
        "X-GAS-Token": WEBHOOK_SECRET,
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true,
    };

    Logger.log("Sending webhook to: " + WEBHOOK_URL);

    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();

    Logger.log("Response code: " + responseCode);
    Logger.log("Response body: " + responseText);

    if (responseCode === 200) {
      Logger.log("✅ Successfully sent webhook for " + studentName);
    } else {
      Logger.log("❌ Webhook failed with code " + responseCode);
    }
  } catch (error) {
    Logger.log("❌ ERROR in onEditInstallable: " + error.toString());
    Logger.log("Stack trace: " + error.stack);
  }
}

/**
 * Конвертирует номер колонки в букву (1 -> A, 27 -> AA)
 */
function columnToLetter(column) {
  let temp;
  let letter = "";
  while (column > 0) {
    temp = (column - 1) % 26;
    letter = String.fromCharCode(temp + 65) + letter;
    column = (column - temp - 1) / 26;
  }
  return letter;
}

/**
 * Функция для создания триггера программно
 * Запустите её ОДИН РАЗ вручную!
 */
function createEditTrigger() {
  // Удаляем старые триггеры для этой функции
  const triggers = ScriptApp.getProjectTriggers();
  for (let i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "onEditInstallable") {
      ScriptApp.deleteTrigger(triggers[i]);
      Logger.log("Deleted old trigger");
    }
  }

  // Создаем новый триггер
  ScriptApp.newTrigger("onEditInstallable")
    .forSpreadsheet(SpreadsheetApp.getActive())
    .onEdit()
    .create();

  Logger.log("✅ Trigger created successfully!");
  Logger.log("Function: onEditInstallable");
  Logger.log("Now edit a grade cell to test");
}

/**
 * Тестовая функция для проверки webhook
 * Запустите её вручную для проверки связи
 */
function testWebhook() {
  Logger.log("=== Testing webhook ===");

  const testPayload = {
    spreadsheetId: SpreadsheetApp.getActiveSpreadsheet().getId(),
    sheetName: "Test",
    subject: "Тестовий предмет",
    studentName: "Бологан Данііл Максимович", // ТОЧНО как в БД!
    lessonType: "Лекція",
    lessonDate: "10.11.2025",
    columnLetter: "D",
    rowIndex: 4,
    oldValue: "",
    newValue: "10",
    timestamp: new Date().toISOString(),
  };

  Logger.log("Test payload: " + JSON.stringify(testPayload));

  const options = {
    method: "post",
    contentType: "application/json",
    headers: {
      "X-GAS-Token": WEBHOOK_SECRET,
    },
    payload: JSON.stringify(testPayload),
    muteHttpExceptions: true,
  };

  Logger.log("Sending to: " + WEBHOOK_URL);

  try {
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();

    Logger.log("Response code: " + responseCode);
    Logger.log("Response body: " + responseText);

    if (responseCode === 200) {
      Logger.log("✅ Test webhook SUCCESS!");
    } else {
      Logger.log("❌ Test webhook FAILED");
    }
  } catch (error) {
    Logger.log("❌ ERROR: " + error.toString());
  }
}

/**
 * Функция для просмотра всех триггеров
 */
function listTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  Logger.log("=== Installed Triggers ===");
  Logger.log("Total triggers: " + triggers.length);

  for (let i = 0; i < triggers.length; i++) {
    const trigger = triggers[i];
    Logger.log("Trigger " + (i + 1) + ":");
    Logger.log("  Function: " + trigger.getHandlerFunction());
    Logger.log("  Event type: " + trigger.getEventType());
    Logger.log("  Source: " + trigger.getTriggerSource());
  }
}

const WEBHOOK_URL = 'https://your-server.com/webhook/grades';
const WEBHOOK_SECRET = 'your_secret_here';

function onEdit(e) {
  try {
    const sheet = e.source.getActiveSheet();
    const sheetName = sheet.getName();
    const spreadsheetId = e.source.getId();
    
    const firstSheet = e.source.getSheets()[0];
    if (sheet.getSheetId() === firstSheet.getSheetId()) {
      Logger.log('Edit in first sheet (roster), ignoring');
      return;
    }
    
    const range = e.range;
    const row = range.getRow();
    const column = range.getColumn();
    
    if (row <= 3 || column < 4) {
      Logger.log('Edit outside grade area, ignoring');
      return;
    }
    
    const subject = sheet.getRange('A1').getValue() || sheetName;
    
    const lessonType = sheet.getRange(2, column).getValue() || '';
    const lessonDate = sheet.getRange(3, column).getValue() || '';
    
    const studentName = sheet.getRange(row, 3).getValue();
    
    if (!studentName) {
      Logger.log('No student name in row ' + row);
      return;
    }
    
    const oldValue = e.oldValue || '';
    const newValue = e.value || '';
    
    const columnLetter = columnToLetter(column);
    
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
      timestamp: new Date().toISOString()
    };
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'X-GAS-Token': WEBHOOK_SECRET
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    const responseCode = response.getResponseCode();
    
    if (responseCode === 200) {
      Logger.log('Successfully sent webhook for ' + studentName);
    } else {
      Logger.log('Webhook failed with code ' + responseCode + ': ' + response.getContentText());
    }
    
  } catch (error) {
    Logger.log('Error in onEdit: ' + error.toString());
  }
}

function columnToLetter(column) {
  let temp;
  let letter = '';
  while (column > 0) {
    temp = (column - 1) % 26;
    letter = String.fromCharCode(temp + 65) + letter;
    column = (column - temp - 1) / 26;
  }
  return letter;
}

function testWebhook() {
  const testPayload = {
    spreadsheetId: SpreadsheetApp.getActiveSpreadsheet().getId(),
    sheetName: 'Test',
    subject: 'Математика',
    studentName: 'Іванов Іван Іванович',
    lessonType: 'Лекція',
    lessonDate: '12.09.2025',
    columnLetter: 'D',
    rowIndex: 4,
    oldValue: '',
    newValue: '10',
    timestamp: new Date().toISOString()
  };
  
  const options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'X-GAS-Token': WEBHOOK_SECRET
    },
    payload: JSON.stringify(testPayload),
    muteHttpExceptions: true
  };
  
  const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
  Logger.log('Test response: ' + response.getContentText());
}

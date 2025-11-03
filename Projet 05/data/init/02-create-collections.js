// 02-create-collections.js
db = db.getSiblingDB('medical_data');

db.createCollection("admissions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["patient", "admission", "medical"],
      properties: {
        patient: {
          bsonType: "object",
          required: ["name", "age", "gender", "blood_type", "insurance_provider"],
          properties: {
            name: { bsonType: "string" },
            age: { bsonType: "int" },
            gender: { enum: ["Male", "Female"] },
            blood_type: { enum: ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] },
            insurance_provider: { enum: ["Aetna", "Blue Cross", "Cigna", "Medicare", "UnitedHealthcare"] }
          }
        },
        admission: {
          bsonType: "object",
          required: ["date", "type"],
          properties: {
            date: { bsonType: "date" },
            type: { enum: ["Elective", "Emergency", "Urgent"] },
            room_number: { bsonType: ["int", "null"] },
            billing_amount: { bsonType: ["double", "null"] },
            discharge_date: { bsonType: ["date", "null"] },
            doctor: { bsonType: "string" },
            hospital: { bsonType: "string" }
          }
        },
        medical: {
          bsonType: "object",
          required: ["condition", "medication", "test_results"],
          properties: {
            condition: { enum: ["Arthritis", "Asthma", "Cancer", "Diabetes", "Hypertension", "Obesity"] },
            medication: { enum: ["Aspirin", "Ibuprofen", "Lipitor", "Paracetamol", "Penicillin"] },
            test_results: { enum: ["Abnormal", "Inconclusive", "Normal"] }
          }
        }
      }
    }
  }
});

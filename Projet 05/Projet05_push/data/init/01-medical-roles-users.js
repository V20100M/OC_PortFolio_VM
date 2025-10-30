// 01-medical-roles-users.js
// Exécuté automatiquement au premier démarrage (data dir vide)

// Passe sur la base applicative
db = db.getSiblingDB('medical_data');

// ===== RÔLES =====
db.createRole({
  role: "medical_admin",
  privileges: [
    {
      resource: { db: "medical_data", collection: "" },
      actions: [
        "find", "insert", "update", "remove",
        "createCollection", "createIndex", "dropCollection", "dropDatabase",
        "listCollections"
      ]
    }
  ],
  roles: []
});

db.createRole({
  role: "medical_user",
  privileges: [
    {
      resource: { db: "medical_data", collection: "admissions" },
      actions: ["find", "insert", "update", "listCollections"]
    }
  ],
  roles: []
});

db.createRole({
  role: "medical_viewer",
  privileges: [
    {
      resource: { db: "medical_data", collection: "" },
      actions: ["find", "listCollections"]
    }
  ],
  roles: []
});

db.createRole({
  role: "medical_indexer",
  privileges: [
    {
      resource: { db: "medical_data", collection: "" },
      actions: ["createCollection", "createIndex", "collMod", "listCollections"]
    }
  ],
  roles: []
});

// ===== UTILISATEURS =====
db.createUser({
  user: "admin_medical",
  pwd: "Admin@123",
  roles: [{ role: "medical_admin", db: "medical_data" }]
});

db.createUser({
  user: "user_medical",
  pwd: "User@123",
  roles: [{ role: "medical_user", db: "medical_data" }]
});

db.createUser({
  user: "viewer_medical",
  pwd: "Viewer@123",
  roles: [{ role: "medical_viewer", db: "medical_data" }]
});

db.createUser({
  user: "indexer_medical",
  pwd: "Indexer@123",
  roles: [{ role: "medical_indexer", db: "medical_data" }]
});
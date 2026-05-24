from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db, engine
from datetime import datetime
import json

router = APIRouter(prefix="/test", tags=["Testing"])

@router.get("/db-connection")
async def test_database_connection(db: Session = Depends(get_db)):
    """Test database connectivity (SQLite vs PostgreSQL)."""
    try:
        if engine.dialect.name == "sqlite":
            row = db.execute(
                text("SELECT datetime('now'), sqlite_version()")
            ).fetchone()
            return {
                "status": "success",
                "database_connected": True,
                "backend": "sqlite",
                "current_time": str(row[0]),
                "sqlite_version": str(row[1]),
                "message": "SQLite connection OK",
            }
        row = db.execute(
            text("SELECT NOW() as current_time, version() as version")
        ).fetchone()
        return {
            "status": "success",
            "database_connected": True,
            "backend": "postgresql",
            "current_time": str(row[0]),
            "postgres_version": str(row[1]).split(" ")[0],
            "message": "PostgreSQL connection OK",
        }
    except Exception as e:
        return {
            "status": "error",
            "database_connected": False,
            "error": str(e),
        }

@router.post("/driver-data")
async def test_driver_data_insert(
    test_data: dict,
    db: Session = Depends(get_db)
):
    """Test inserting data from driver app"""
    try:
        # Create a test log entry in the database
        timestamp = datetime.now()
        
        # Insert test data (we'll create a simple log table)
        db.execute("""
            CREATE TABLE IF NOT EXISTS driver_test_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                data JSONB,
                source VARCHAR(50) DEFAULT 'driver-app'
            )
        """)
        
        # Insert the test data
        db.execute("""
            INSERT INTO driver_test_logs (data, source) 
            VALUES (:data, :source)
        """, {
            "data": json.dumps(test_data),
            "source": "driver-app"
        })
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Test data successfully inserted to database",
            "timestamp": timestamp.isoformat(),
            "data_received": test_data
        }
        
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Failed to insert test data: {str(e)}"
        }

@router.get("/driver-logs")
async def get_driver_test_logs(db: Session = Depends(get_db)):
    """Get all test logs from driver app"""
    try:
        result = db.execute("""
            SELECT id, timestamp, data, source 
            FROM driver_test_logs 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        logs = []
        for row in result.fetchall():
            logs.append({
                "id": row[0],
                "timestamp": str(row[1]),
                "data": json.loads(row[2]) if row[2] else {},
                "source": row[3]
            })
        
        return {
            "status": "success",
            "logs_count": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch logs: {str(e)}"
        }
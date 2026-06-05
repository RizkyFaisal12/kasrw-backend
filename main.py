from fastapi import FastAPI, HTTPException 
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel 
from typing import Optional 
import mysql.connector 
import os 
from dotenv import load_dotenv 

load_dotenv() 

app = FastAPI(title="Kas RW API") 

app.add_middleware( 
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"], 
) 

def get_db(): 
    return mysql.connector.connect( 
        host="192.168.56.11",               
        port=3306, 
        database="kasrw",       
        user="kasrw",                      
        password="@password123",                 
    ) 

# Mengubah tipe tanggal menjadi str agar aman saat menerima kiriman dari HTML/JS
class TransaksiBase(BaseModel): 
    tanggal: str 
    keterangan: str 
    jenis: str      # 'pemasukan' atau 'pengeluaran' 
    jumlah: float 

class TransaksiUpdate(BaseModel): 
    tanggal: Optional[str] = None 
    keterangan: Optional[str] = None 
    jenis: Optional[str] = None 
    jumlah: Optional[float] = None 

@app.get("/") 
def root(): 
    return {"message": "Kas RW API berjalan"} 

@app.get("/transaksi") 
def get_all(): 
    db = get_db() 
    cursor = db.cursor(dictionary=True) 

    cursor.execute( 
        "SELECT * FROM transaksi ORDER BY tanggal DESC" 
    ) 

    rows = cursor.fetchall() 
    db.close() 

    # Mengubah objek date MySQL menjadi string biasa agar tidak error JSON
    for row in rows:
        if row.get("tanggal"):
            row["tanggal"] = str(row["tanggal"])

    return rows 

@app.get("/transaksi/{id}") 
def get_one(id: int): 
    db = get_db() 
    cursor = db.cursor(dictionary=True) 

    cursor.execute( 
        "SELECT * FROM transaksi WHERE id = %s", 
        (id,) 
    ) 

    row = cursor.fetchone()
    db.close() 

    if not row: 
        raise HTTPException( 
            status_code=404, 
            detail="Transaksi tidak ditemukan" 
        ) 

    if row.get("tanggal"):
        row["tanggal"] = str(row["tanggal"])

    return row 

@app.post("/transaksi", status_code=201) 
def create(data: TransaksiBase): 
    db = get_db() 
    cursor = db.cursor() 

    try:
        cursor.execute(
            "INSERT INTO transaksi (tanggal, keterangan, jenis, jumlah) VALUES (%s, %s, %s, %s)", 
            (data.tanggal, data.keterangan, data.jenis, data.jumlah), 
        ) 
        db.commit() 
        new_id = cursor.lastrowid 
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

    db.close() 

    return { 
        "id": new_id, 
        "message": "Transaksi berhasil ditambahkan" 
    } 

@app.put("/transaksi/{id}") 
def update(id: int, data: TransaksiUpdate): 
    db = get_db() 
    cursor = db.cursor(dictionary=True) 

    cursor.execute( 
        "SELECT * FROM transaksi WHERE id = %s", 
        (id,) 
    ) 

    row = cursor.fetchone() 

    if not row: 
        db.close() 

        raise HTTPException(
            status_code=404, 
            detail="Transaksi tidak ditemukan" 
        ) 

    # Normalisasi tanggal database ke string sebelum digabung
    if row.get("tanggal"):
        row["tanggal"] = str(row["tanggal"])

    updated = { 
        **row, 
        **{ 
            k: v for k, v in data.dict().items() 
            if v is not None 
        } 
    } 

    cursor.execute( 
        """ 
        UPDATE transaksi 
        SET tanggal=%s, 
            keterangan=%s, 
            jenis=%s, 
            jumlah=%s 
        WHERE id=%s 
        """, 
        ( 
            updated["tanggal"], 
            updated["keterangan"], 
            updated["jenis"], 
            updated["jumlah"], 
            id 
        ), 
    ) 

    db.commit() 
    db.close() 

    return { 
        "message": "Transaksi berhasil diperbarui" 
    } 

@app.delete("/transaksi/{id}") 
def delete(id: int): 
    db = get_db() 
    cursor = db.cursor() 

    cursor.execute( 
        "DELETE FROM transaksi WHERE id = %s", 
        (id,) 
    ) 
    db.commit() 

    affected = cursor.rowcount 

    db.close() 

    if affected == 0: 
        raise HTTPException( 
            status_code=404, 
            detail="Transaksi tidak ditemukan" 
        ) 

    return { 
        "message": "Transaksi berhasil dihapus"
    }
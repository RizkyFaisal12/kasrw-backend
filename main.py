import os
import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

app = FastAPI(title="Sistem API Kas RW Sukapura")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TransaksiSchema(BaseModel):
    jenis: str
    tanggal: str
    keterangan: str
    jumlah: float


def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "kasrw"),
        )
        return conn
    except mysql.connector.Error as err:
        print("MYSQL ERROR:", err)
        raise HTTPException(status_code=500, detail=f"DB Error: {err}")


@app.get("/saldo")
async def get_ringkasan_saldo():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT SUM(jumlah) AS total FROM transaksi WHERE jenis='pemasukan'")
        pemasukan = cursor.fetchone()["total"] or 0

        cursor.execute("SELECT SUM(jumlah) AS total FROM transaksi WHERE jenis='pengeluaran'")
        pengeluaran = cursor.fetchone()["total"] or 0

        cursor.execute("SELECT COUNT(*) AS total FROM transaksi")
        jumlah_transaksi = cursor.fetchone()["total"] or 0

        return {
            "saldo": float(pemasukan - pengeluaran),
            "total_pemasukan": float(pemasukan),
            "total_pengeluaran": float(pengeluaran),
            "jumlah_transaksi": jumlah_transaksi,
        }
    finally:
        cursor.close()
        conn.close()


@app.get("/transaksi")
async def get_all_transaksi():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM transaksi ORDER BY id DESC")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


@app.post("/transaksi", status_code=status.HTTP_201_CREATED)
async def create_transaksi(payload: TransaksiSchema):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO transaksi (jenis, tanggal, keterangan, jumlah) VALUES (%s, %s, %s, %s)",
            (payload.jenis, payload.tanggal, payload.keterangan, payload.jumlah)
        )
        conn.commit()
        return {"status": "success", "inserted_id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()


@app.put("/transaksi/{transaksi_id}")
async def update_transaksi(transaksi_id: int, payload: TransaksiSchema):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE transaksi SET jenis=%s, tanggal=%s, keterangan=%s, jumlah=%s WHERE id=%s",
            (payload.jenis, payload.tanggal, payload.keterangan, payload.jumlah, transaksi_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
        return {"status": "success", "updated_id": transaksi_id}
    finally:
        cursor.close()
        conn.close()


@app.delete("/transaksi/{transaksi_id}")
async def delete_transaksi(transaksi_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM transaksi WHERE id=%s", (transaksi_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
        return {"status": "success", "deleted_id": transaksi_id}
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
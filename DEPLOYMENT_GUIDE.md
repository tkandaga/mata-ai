# 🚀 MATA v2.5 - Railway Deployment Guide

## 📋 Checklist Sebelum Deploy

### ✅ File Yang HARUS Ada (Sudah Siap!)
- [x] `mata_v2.5.py` - Backend Flask application
- [x] `index.html` - Frontend interface
- [x] `login.html` - Login page
- [x] `requirements.txt` - Python dependencies
- [x] `Procfile` - Railway start command
- [x] `runtime.txt` - Python version specification
- [x] `.gitignore` - Exclude unnecessary files
- [x] `README.md` - Documentation

### 🔧 Konfigurasi Yang Sudah Diterapkan
- [x] Port configuration menggunakan environment variable `PORT`
- [x] Debug mode auto-disabled untuk production
- [x] CORS enabled untuk frontend-backend communication
- [x] Static files serving

---

## 🎯 Langkah-Langkah Deploy ke Railway.app

### Step 1: Persiapan Repository GitHub

1. **Buat Repository Baru di GitHub**
   - Buka https://github.com/new
   - Beri nama repository (contoh: `mata-v2-tutoring`)
   - Pilih **Public** atau **Private** (terserah)
   - **JANGAN** centang "Initialize with README" (karena sudah ada)
   - Klik **Create repository**

2. **Upload Project ke GitHub**
   
   Buka terminal/command prompt di folder project ini, lalu jalankan:
   
   ```bash
   git init
   git add .
   git commit -m "Initial commit - MATA v2.5 ready for Railway"
   git branch -M main
   git remote add origin https://github.com/USERNAME/REPO_NAME.git
   git push -u origin main
   ```
   
   **Ganti:**
   - `USERNAME` dengan username GitHub Anda
   - `REPO_NAME` dengan nama repository yang Anda buat

### Step 2: Deploy ke Railway.app

1. **Login ke Railway**
   - Buka https://railway.app
   - Klik **Login** (bisa pakai GitHub account)

2. **Buat Project Baru**
   - Klik **New Project**
   - Pilih **Deploy from GitHub repo**
   - Pilih repository yang baru Anda buat
   - Railway akan otomatis mendeteksi Python project

3. **Configure Environment Variables**
   
   Railway akan auto-deploy, tapi Anda HARUS set API keys:
   
   - Di Railway dashboard, klik project Anda
   - Klik tab **Variables**
   - Tambahkan variable berikut:

   | Variable Name | Value | Keterangan |
   |--------------|-------|------------|
   | `CLAUDE_API_KEY` | `sk-ant-api...` | API key dari Anthropic Claude |
   | `OPENAI_API_KEY` | `sk-...` | API key dari OpenAI (opsional) |
   | `FLASK_ENV` | `production` | Set ke production mode |

   **Cara Mendapatkan API Keys:**
   - **Claude API**: https://console.anthropic.com/account/keys
   - **OpenAI API**: https://platform.openai.com/api-keys

4. **Deploy!**
   - Setelah set environment variables, klik **Deploy**
   - Tunggu proses build selesai (~2-5 menit)
   - Railway akan memberikan public URL (contoh: `https://mata-v2-production.up.railway.app`)

### Step 3: Update Frontend URL

Setelah deploy selesai, Anda perlu update URL backend di `index.html`:

1. Copy URL dari Railway (contoh: `https://mata-v2-production.up.railway.app`)
2. Buka file `index.html`
3. Cari baris yang ada `http://localhost:8090` atau `http://localhost:5000`
4. Ganti dengan URL Railway Anda
5. Commit dan push perubahan:
   ```bash
   git add index.html
   git commit -m "Update backend URL to Railway"
   git push
   ```

Railway akan otomatis re-deploy setelah ada push baru!

---

## 🔑 Cara Mendapatkan API Keys

### Claude API (Anthropic)
1. Buka https://console.anthropic.com
2. Login atau sign up
3. Pergi ke **API Keys** di sidebar
4. Klik **Create Key**
5. Copy API key (format: `sk-ant-api...`)
6. **PENTING**: Top up credit di https://console.anthropic.com/settings/billing

### OpenAI API (Opsional)
1. Buka https://platform.openai.com
2. Login atau sign up
3. Pergi ke **API Keys**
4. Klik **Create new secret key**
5. Copy API key (format: `sk-...`)
6. **PENTING**: Add payment method di https://platform.openai.com/settings/billing

---

## 🧪 Testing Setelah Deploy

1. **Test Backend**
   - Buka: `https://YOUR-RAILWAY-URL.up.railway.app/api/conversation-stats`
   - Harus muncul JSON response seperti:
     ```json
     {
       "success": true,
       "session_id": "new",
       "conversation_count": 0
     }
     ```

2. **Test Frontend**
   - Buka URL Railway di browser
   - Login dengan username dan password
   - Coba kirim pertanyaan
   - Pastikan response dari AI muncul

---

## 🐛 Troubleshooting

### Error: "Application failed to respond"
**Solusi:**
- Check Logs di Railway dashboard
- Pastikan `Procfile` ada dan benar
- Pastikan `requirements.txt` complete
- Check environment variable `PORT` sudah di-set Railway (otomatis)

### Error: "API key not found"
**Solusi:**
- Check environment variables di Railway dashboard
- Pastikan `CLAUDE_API_KEY` atau `OPENAI_API_KEY` sudah di-set
- Re-deploy setelah add variables

### Error: "Module not found"
**Solusi:**
- Check `requirements.txt` sudah lengkap
- Railway akan auto-install dari requirements.txt
- Check build logs untuk error details

### Frontend tidak connect ke backend
**Solusi:**
- Pastikan URL backend di `index.html` sudah diganti ke Railway URL
- Check CORS enabled di backend (sudah enabled)
- Check network tab di browser developer tools

---

## 💰 Railway Pricing

Railway menggunakan model **Pay-as-you-go**:

- **Free tier**: $5 credit per month (cukup untuk development/testing)
- **Usage-based**: ~$0.000463 per GB-minute (resource usage)
- **Tips menghemat**:
  - Set auto-sleep jika tidak ada traffic
  - Monitor usage di dashboard
  - Upgrade ke plan berbayar jika perlu ($5-$20/bulan)

---

## 🎉 Selamat!

Aplikasi MATA v2.5 Anda sudah live di Railway! 

**URL Aplikasi**: `https://YOUR-RAILWAY-URL.up.railway.app`

### Next Steps:
1. ✅ Share URL dengan users
2. ✅ Monitor logs dan usage di Railway dashboard
3. ✅ Update API keys jika habis credit
4. ✅ Add custom domain (opsional, di Railway settings)

---

## 📞 Support

Jika ada masalah:
1. Check Railway logs: Dashboard > Deployments > View Logs
2. Check GitHub issues
3. Railway Discord: https://discord.gg/railway
4. Anthropic Support: https://support.anthropic.com

---

**Created by**: MATA v2.5 Team  
**Last Updated**: October 2025


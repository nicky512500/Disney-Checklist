# Disney 宇宙片單 Checklist

可勾選追蹤觀影進度的 Disney / Pixar / Marvel / Star Wars / 20th Century / Searchlight / Disney Channel 片單。

## 本機開發

```bash
python3 fetch_disney.py        # 從 TMDb 抓取最新片單 → tmdb_data.json
python3 generate_checklist.py  # 生成 data.js
python3 -m http.server 8000    # 本機預覽 http://localhost:8000
```

`fetch_disney.py` 需要 `.env`:

```
TMDB_API_KEY=你的TMDb_API_KEY
```

## 部署到 GitHub Pages

只需 `index.html`、`data.js`、`firebase-config.js` 三個檔。Push 到 GitHub repo → Settings → Pages → Source: `main` branch / root。

## 跨裝置同步 (Firebase)

預設只用 localStorage,進度綁定瀏覽器。要跨裝置同步請依下面步驟設定 Firebase
(免費)。

### 1. 建立 Firebase 專案

1. 開 [Firebase Console](https://console.firebase.google.com) → Add project
2. 取個名字 (例如 `disney-list`) → 可關閉 Google Analytics → Create

### 2. 啟用 Authentication

1. 左側 Build → Authentication → Get started
2. Sign-in method → Google → Enable → 填 support email → Save
3. Settings → Authorized domains → Add domain → 填你的 GitHub Pages 網域
   (例如 `<你的帳號>.github.io`)

### 3. 啟用 Firestore

1. 左側 Build → Firestore Database → Create database
2. Location 選離你最近的 (台灣選 `asia-east1`)
3. 模式選 **Production mode** → Enable
4. Rules 分頁,貼上以下規則然後 Publish:

   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /lists/{userId} {
         allow read, write: if request.auth != null
           && request.auth.uid == userId;
       }
     }
   }
   ```

### 4. 取得 web config 並貼進 `firebase-config.js`

1. Project Overview → Add app → `</>` (Web) → 註冊 app (不用勾 Hosting)
2. 複製顯示的 `firebaseConfig` 物件,貼進 `firebase-config.js`:

   ```js
   window.firebaseConfig = {
     apiKey: "AIza...",
     authDomain: "disney-list.firebaseapp.com",
     projectId: "disney-list",
     appId: "1:..."
   };
   ```

3. Commit + push,網頁右上會出現「用 Google 登入同步」按鈕。

Firebase web 設定可公開,安全性由上面的 Firestore Rules 把關:每個使用者只能讀寫
自己 UID 的文件。

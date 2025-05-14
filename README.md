# 🗳️ Blockchain Ovoz Berish Tizimi (Flask + Solidity)

Bu loyiha Flask va Solidity yordamida qurilgan, foydalanuvchilar Ethereum blockchain asosida xavfsiz ovoz berishda ishtirok etishlari mumkin bo‘lgan tizimdir. Har bir saylov alohida `Voting.sol` kontrakti sifatida blockchain'ga joylanadi.

---

## ✨ Asosiy imkoniyatlar

- Har bir saylov uchun alohida `Voting.sol` smart-kontrakt deploy qilinadi
- Nomzodlar faqat saylov boshlanishidan oldin qo‘shilishi mumkin
- Har foydalanuvchi faqat bir marta ovoz bera oladi
- Ovozlar Ethereum blockchain'da saqlanadi
- Saylov natijalari  jadval ko‘rinishida ko‘rsatiladi
- Natijalarni CSV holatda yuklab olish mumkin
- Admin panel orqali foydalanuvchilar va saylovlar boshqariladi

---

## 🧱 Texnologiyalar

- `Python 3.10+`
- `Flask`
- `Solidity`
- `Web3.py`
- `Ganache CLI`
- `Bootstrap 5 + Chart.js`
- `SQLite`

---

## ⚙️ O‘rnatish

### 1. Repository’ni klon qilish

```bash
git clone https://github.com/MuxammadiyevG/ChainVoting.git
cd ChainVoting
```

```bash 
python3 -m venv .venv
pip install -r requirements.txt
```
## Blockchain blocklarini saqlash uchun Ganache test tarmog'idan foydalanamiz .

## Ganacheni o'rnatish
```bash
- 'Arch linux' `yay -S ganache-cli`
- boshqa dirstolarda (Windows , va hk ) ```bash npm install -g ganache-cli ```

## Ganacheni ishga tushirish
```bash
ganache-cli --host 127.0.0.1 --port 7545 
```
![alt text](image.png)

### Ixtiyoriy kalit juftligini olib .env ga joylaysiz

```python
BLOCKCHAIN_PROVIDER=http://127.0.0.1:7545
ADMIN_ADDRESS=0xyour_address
ADMIN_PRIVATE_KEY=0xyour_private_key
```

# Ganachega backendimizni bog'lash uchun Voting.solni compilatsiya qilamiz. 

```bash
python3 contracts/compile.py
```

## Shuning bilan dastur ishga tushirilishga tayyor 

```bash
python3 app.py
```
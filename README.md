# 🛡️ WinDefenderRemote

**Удалённое управление Windows Defender через системный трей**

[![GitHub release](https://img.shields.io/github/v/release/wemble468/WinDefenderRemote?style=flat-square)](https://github.com/wemble468/WinDefenderRemote/releases)
[![Downloads](https://img.shields.io/github/downloads/wemble468/WinDefenderRemote/total?style=flat-square)](https://github.com/wemble468/WinDefenderRemote/releases)
[![Platform](https://img.shields.io/badge/Windows-10%20%7C%2011-blue?style=flat-square)](https://github.com/wemble468/WinDefenderRemote)

---

## 📌 Описание

**WinDefenderRemote** — это небольшая утилита для Windows, которая позволяет управлять **Microsoft Defender** прямо из системного трея.  
Программа работает в фоне, не требует установки и поддерживает **синхронизацию через GitHub** для управления несколькими ПК.

---

## ✨ Возможности

| Функция | Описание |
|---------|----------|
| ⚡ **Быстрая проверка** | Запускает быструю проверку Defender |
| 🔍 **Полная проверка** | Запускает полную проверку Defender |
| 📊 **Статус Defender** | Показывает текущее состояние защиты |
| ⛔ **Отключить Defender** | Отключает защиту в реальном времени |
| ✅ **Включить Defender** | Включает защиту обратно |
| 💤 **Wake-on-LAN** | Включает удалённый ПК по сети |
| 🌐 **GitHub синхронизация** | Синхронизирует команды между ПК |
| 🔒 **Работа в трее** | Иконка в системном трее, без окон |

---

## 📥 Скачать

**Последняя версия:** [WinDefenderRemote.exe](https://github.com/wemble468/WinDefenderRemote/releases/latest/download/WinDefenderRemote.exe)

---

## 🚀 Быстрый старт

1. **Скачай** `WinDefenderRemote.exe`
2. **Запусти** файл (можно без установки)
3. **Иконка** появится в системном трее (рядом с часами)
4. **Нажми правой кнопкой** на иконку → выбери действие

---

## ⚙️ Настройка GitHub (опционально)

Чтобы синхронизировать команды между ПК:

1. **Создай репозиторий** на GitHub (например, `WinDefenderRemote-Data`)
2. **Создай Personal Access Token** с правами `repo`
3. **Заполни `config.json`** (создаётся автоматически при первом запуске):

```json
{
  "GITHUB_TOKEN": "ghp_твой_токен",
  "GITHUB_OWNER": "твой_username",
  "GITHUB_REPO": "WinDefenderRemote-Data"
}

# AI-SOP-Protocol — Makefile
# 目的：專案層級設定 + 載入 ASP targets
# 使用方式：在 include 之前加入專案自訂 targets

APP_NAME ?= Athena
VERSION  ?= latest

# --- 專案自訂 targets 請寫在此區塊 ---


# ASP targets（勿刪除此行）
-include .asp/Makefile.inc

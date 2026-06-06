# Entro Test Demo

Đây là một **demo module** do **Dev Agent** tạo ra trong khuôn khổ
**Phase 2 verification** của hệ thống Entro Auto-Workflow.

## Mục đích

- Verify end-to-end flow của Dev Agent: đọc task → tạo branch → tạo file →
  commit → push → mở PR → cập nhật task tracker.
- Không chứa bất kỳ model, view, hay business logic nào.
- Chỉ depends vào `base` để có thể install/uninstall an toàn trên DB test.

## ⚠️ KHÔNG dùng cho production

Module này chỉ phục vụ verification nội bộ Phase 2. **KHÔNG** cài đặt
trên môi trường production. Có thể xoá bất cứ lúc nào sau khi verification
hoàn tất mà không ảnh hưởng đến các module HRM khác.

## Task tham chiếu

- **Task ID**: `phase2-tuan10`
- **Title**: Create demo module 'entro_test_demo' (Phase 2 verification)
- **Branch**: `feat/T-phase2-tuan10-demo-module`

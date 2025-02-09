
### Базовые Модели
- **BaseMessage**: Основа для всех сообщений с полем `type` для указания типа сообщения.

### Ответы и Запросы
- **ErrorResponse**: Сообщение об ошибке с `message`.
- **SuccessResponse**: Успешный ответ с полем `data`.
- **TokenRefreshRequest**: Запрос на обновление токена с `access_token`.
- **AdminLoginHTTP**: Данные для входа администратора с `username` и `password`.
- **UserInfo**: Информация о пользователе, включая `nickname` и `id`.

### Взаимодействие с Пользователем
- **LoginData**: Данные для логина пользователя с `nickname` и опциональным `user_id`.
- **PixelInfoData** и **Pixel**: Данные о пикселе, включая координаты (`x`, `y`), `color`, и информацию о пользователе.
- **Selection**: Выбранная область или объект пользователем.
- **CoolDownData**: Данные о времени ожидания (cooldown).
- **FieldStateData**: Состояние игрового поля или области с `pixels` и `selections`.

### Обновления и Уведомления
- **PixelUpdateData** и **SelectionUpdateData**: Данные для обновления пикселей и выбранных областей.
- **SelectionUpdateRequest** и **PixelUpdateRequest**: Запросы на обновление.
- **SelectionUpdateBroadcast** и **PixelUpdateNotification**: Трансляция обновлений другим пользователям.
- **ChangeCooldownResponse** и **ChangeCooldownRequest**: Ответы и запросы на изменение времени ожидания.

### Административное Управление
- **LoginRequest** и **AuthResponse**: Запросы и ответы для аутентификации пользователей и администраторов.
- **AdminLoginRequest**: Запрос на вход для администратора.
- **OnlineCountResponse** и **UserInfoResponse**: Информация о количестве онлайн пользователей и детальная информация о пользователях.
- **FieldStateResponse**: Ответ с состоянием поля или рабочей области.
- **PixelInfoRequest** и **PixelInfoResponse**: Запрос и ответ с информацией о пикселе для администраторов.
- **BanUserRequest**: Запрос на блокировку пользователя.
- **ResetGameRequest**: Запрос на сброс игры или состояния приложения.

Эти модели формируют основу для обеспечения взаимодействия пользователя с системой через вебсокеты и HTTP-точки доступа, включая аутентификацию, управление состоянием и административные функции. Модели позволяют организовать обмен данными между клиентом и сервером, предоставляя возможности для реализации сложных взаимодействий в приложении, от управления состоянием объектов до административного контроля и мониторинга активности пользователей.
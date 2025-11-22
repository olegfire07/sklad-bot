# Modern Bot

This is the refactored and improved version of the conclusion bot, featuring a standalone web app mode.

## Features
- **Modular Structure**: Clean code organized in `modern_bot/`.
- **Web App**: "Fool-proof" data entry via a Telegram Mini App.
- **Standalone Mode**: Use the Web App in any browser (Chrome, Safari) to generate documents without Telegram.
- **Monetization**: `/broadcast` command to send messages to all users.
- **Improved Reports**: Better archive handling and stats.

## How to Run
1.  Ensure you are in the project root (`/Users/oleg/Project_SKLAD`).
2.  Run the bot:
    ```bash
    python3 run_modern_bot.py
    ```
3.  **For Standalone Mode**: Start the ngrok tunnel:
    ```bash
    ./start_tunnel.sh
    ```
    *Note: The default URL in `index.html` is set to a specific ngrok address. If your tunnel URL changes, you must update it in the Web App settings.*

## Web App Setup
To use the Web App:
1.  Host the file `modern_bot/web_app/index.html` on a public server (GitHub Pages).
2.  **Standalone Access**: Open the GitHub Pages URL directly in your browser.
    - If the "Bot URL" is not configured or incorrect, the app will prompt you to enter it (e.g., your ngrok URL).
    - **Secret Settings**: Tap the "Новое заключение" title 5 times rapidly to open settings manually.

## Admin Commands
- `/add_admin <ID>`
- `/broadcast <Message>`
- `/download_month <MM.YYYY>`
- `/stats`

## Architecture & Flows

### Settings & Configuration Flow
```mermaid
sequenceDiagram
    actor "User" as User
    participant "Main Title" as MainTitle
    participant "Settings Modal" as SettingsModal
    participant "Local Storage" as LocalStorage
    participant "App Config" as AppConfig

    "User"->>"Main Title": "Click title (x5)"
    "Main Title"->>"Main Title": "Increment titleClicks"
    "Main Title"-->>"Main Title": "titleClicks >= 5?"
    alt "Reached 5 clicks"
        "Main Title"->>"Settings Modal": "Display settingsModal"
        "Settings Modal"->>"Local Storage": "Read 'imgbb_key' and 'bot_url' (already loaded into variables)"
        "Settings Modal"->>"Settings Modal": "Set 'apiKeyInput.value' = imgbbKey"
        "Settings Modal"->>"Settings Modal": "Set 'botUrlInput.value' = botUrl"
        "Main Title"->>"Main Title": "Reset titleClicks to 0"
    end

    "User"->>"Settings Modal": "Edit ImgBB key and Bot URL"
    "User"->>"Settings Modal": "Click 'Save' button"
    "Settings Modal"->>"Settings Modal": "saveSettings() reads apiKeyInput, botUrlInput"

    alt "ImgBB key is non-empty"
        "Settings Modal"->>"Local Storage": "Set 'imgbb_key' = key"
        "Settings Modal"->>"Settings Modal": "imgbbKey = key"
    else "ImgBB key is empty"
        "Settings Modal"->>"Local Storage": "Remove 'imgbb_key'"
        "Settings Modal"->>"App Config": "Read DEFAULT_IMGBB_KEY"
        "Settings Modal"->>"Settings Modal": "imgbbKey = APP_CONFIG.DEFAULT_IMGBB_KEY"
    end

    alt "Bot URL input is non-empty"
        "Settings Modal"->>"Settings Modal": "cleanUrl = url without trailing slash"
        "Settings Modal"->>"Local Storage": "Set 'bot_url' = cleanUrl"
        "Settings Modal"->>"Settings Modal": "botUrl = cleanUrl"
    else "Bot URL input is empty or undefined"
        "Settings Modal"->>"Local Storage": "Remove 'bot_url'"
        "Settings Modal"->>"App Config": "Read DEFAULT_BOT_URL"
        "Settings Modal"->>"Settings Modal": "botUrl = APP_CONFIG.DEFAULT_BOT_URL"
    end

    "Settings Modal"->>"Settings Modal": "Hide settingsModal"
```

### Submission Flow
```mermaid
sequenceDiagram
    actor "User" as User
    participant "Main Form" as MainForm
    participant "Telegram WebApp" as Telegram
    participant "Settings Modal" as SettingsModal
    participant "Local Storage" as LocalStorage
    participant "Bot Backend" as BotBackend

    "User"->>"Main Form": "Click 'Проверить и отправить'"
    "Main Form"->>"Main Form": "showPreview() and prepare data object"

    "User"->>"Main Form": "Confirm send"
    "Main Form"->>"Main Form": "Disable send button, set text 'Отправка...'"

    "Main Form"->>"Telegram": "Check tg.initDataUnsafe and tg.initDataUnsafe.user"
    alt "Running inside Telegram"
        "Main Form"->>"Telegram": "tg.sendData(JSON.stringify(data))"
        "Telegram"-->>"Main Form": "Sending to bot via Telegram platform"
        "Main Form"->>"Main Form": "Re-enable UI as needed"
    else "Standalone browser mode"
        "Main Form"->>"Main Form": "Check botUrl value"
        alt "botUrl is empty or missing"
            "Main Form"->>"Settings Modal": "Display settingsModal"
            "Main Form"->>"Telegram": "tg.showAlert('Нужно указать URL бота...')"
            "Main Form"->>"Main Form": "Re-enable send button, set text 'Отправить'"
        else "botUrl is configured"
            "Main Form"->>"Bot Backend": "Send data to botUrl (HTTP request)"
            "Bot Backend"-->>"Main Form": "Respond with success or error"
            "Main Form"->>"Main Form": "Handle response, re-enable send button"
        end
    end
```

### Initialization Logic
```mermaid
flowchart TD
    A_Start["Start app"]
    A_Start-->A_LoadImgBB["Load 'imgbb_key' from Local Storage"]
    A_LoadImgBB-->A_ImgBBExists{"'imgbb_key' exists?"}
    A_ImgBBExists-->|"Yes"|A_SetImgBBFromStorage["Set imgbbKey = stored value"]
    A_ImgBBExists-->|"No"|A_SetImgBBDefault["Set imgbbKey = APP_CONFIG.DEFAULT_IMGBB_KEY"]

    A_SetImgBBFromStorage-->A_LoadBotUrl["Load 'bot_url' from Local Storage"]
    A_SetImgBBDefault-->A_LoadBotUrl
    A_LoadBotUrl-->A_BotUrlExists{"'bot_url' exists?"}
    A_BotUrlExists-->|"Yes"|A_SetBotUrlFromStorage["Set botUrl = stored value"]
    A_BotUrlExists-->|"No"|A_SetBotUrlDefault["Set botUrl = APP_CONFIG.DEFAULT_BOT_URL"]

    A_SetBotUrlFromStorage-->A_Wait["Wait for user actions"]
    A_SetBotUrlDefault-->A_Wait

    subgraph B_Settings_Modal_Open ["B_Settings Modal Open"]
        B_Open["User clicks title 5 times"]-->B_ShowModal["Show settingsModal"]
        B_ShowModal-->B_Prefill["Prefill apiKeyInput = imgbbKey, botUrlInput = botUrl"]
    end

    A_Wait-->B_Open

    subgraph C_Save_Settings ["C_Save Settings"]
        C_UserSave["User clicks 'Сохранить'"]-->C_ReadInputs["Read apiKeyInput and botUrlInput"]
        C_ReadInputs-->C_ImgBBNonEmpty{"ImgBB key non-empty?"}
        C_ImgBBNonEmpty-->|"Yes"|C_SaveImgBB["Save 'imgbb_key' to Local Storage and set imgbbKey = key"]
        C_ImgBBNonEmpty-->|"No"|C_ResetImgBB["Remove 'imgbb_key'; set imgbbKey = APP_CONFIG.DEFAULT_IMGBB_KEY"]

        C_SaveImgBB-->C_BotUrlNonEmpty{"Bot URL non-empty?"}
        C_ResetImgBB-->C_BotUrlNonEmpty
        C_BotUrlNonEmpty-->|"Yes"|C_CleanAndSaveUrl["Remove trailing slash; save 'bot_url'; set botUrl = cleanUrl"]
        C_BotUrlNonEmpty-->|"No"|C_ResetBotUrl["Remove 'bot_url'; set botUrl = APP_CONFIG.DEFAULT_BOT_URL"]

        C_CleanAndSaveUrl-->C_CloseModal["Hide settingsModal"]
        C_ResetBotUrl-->C_CloseModal
    end

    B_Prefill-->C_UserSave
    C_CloseModal-->A_Wait
```

## 1. Подготовка окружения

- Установить [Node.js](https://nodejs.org/) (LTS версия).
    
- Создать новый проект:
    
```sh
    npx create-next-app@latest ProjectName
    cd my-ai-chat
```
    
- Установить зависимости:
    
```sh
    npm install ai @ai-sdk/openai
    npm install --save-dev @types/node :: Основные зависимости
    npm install ai @openrouter/ai-sdk-provider :: Зависит от провайдера, для каждого своя зависимость
	npx ai-elements@latest :: Готовые элементы
	npm install ai :: Для useChat
```

## 2. Бэкенд (API route)

Создать файл `app/api/chat/route.ts`:
Отвечает за обработку запросов, api ключ подтягивается из .env
В корне проекта создал файл .env:
OPENROUTER_API_KEY=sk-or-v1-xxx
Важно указать export const runtime = 'nodejs'; чтобы Vercel подтянул ключ и .env
Если все в порядке Vercel сам задеплоит проект и даст ссылку, однако для api ключа нужно отдельно добавить его в .env
- На [dashboard.vercel.com](https://vercel.com/dashboard) → Project Settings → Environment Variables добавить:

```
key = OPENROUTER_API_KEY
value = sk-or-v1-xxxx
```

```ts
import { createOpenRouter } from '@openrouter/ai-sdk-provider';
import { streamText, UIMessage, convertToModelMessages } from 'ai';

export const maxDuration = 30;
export const runtime = 'nodejs';

const openrouter = createOpenRouter({
  apiKey: process.env.OPENROUTER_API_KEY!,  
});
  
export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();
  console.log("Получены сообщения:", messages);

  const modelMessages = convertToModelMessages(messages);

  const result = streamText({
    model: openrouter('x-ai/grok-4-fast:free'),
    messages: modelMessages,
  });
  return result.toUIMessageStreamResponse();
}
```

## 3. Фронтенд (страница с чатом)

`app/page.tsx`:
Отвечает за отрисовку страниц

```tsx
'use client';

import { useState } from 'react';
import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';

export default function ChatPage() {
  const [input, setInput] = useState('');
  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({
      api: '/api/chat',
    }),
  });

  return (
    <div className="flex flex-col w-full max-w-md py-24 mx-auto">
      <div className="flex-1 overflow-y-auto space-y-2">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`whitespace-pre-wrap p-2 rounded ${
              message.role === 'user' ? 'bg-blue-100 text-right ml-auto' : 'bg-gray-100 text-left mr-auto'
            }`}
          >
            <strong>{message.role === 'user' ? 'Вы: ' : 'Бот: '}</strong>
            {message.parts.map((part: any, i: number) => {
              if (part.type === 'text') return <div key={i}>{part.text}</div>;
              return null;
            })}
          </div>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!input.trim()) return;
          sendMessage({ text: input });
          setInput('');
        }}
        className="mt-4 flex gap-2"
      >
        <input
          type="text"
          className="flex-1 p-2 border rounded"
          placeholder="Напишите сообщение..."
          value={input}
          onChange={(e) => setInput(e.currentTarget.value)}
          disabled={status !== 'ready'}
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-500 text-white rounded"
          disabled={status !== 'ready' || !input.trim()}
        >
          Отправить
        </button>
      </form>
    </div>
  );
}
```

## 4. Запуск локально
После этого можно запускать локально и тестировать

```sh
npm run dev
```

Открой [http://localhost:3000](http://localhost:3000/) → чат должен работать

## 5. Деплой на Vercel
Для начала нужно создать репозиторий, я создал пустой на github, после этого запустил git bash:
git init `инициализировал репозиторий`
git remote add https://github.com/Namelomax/AISDK `Подключил к удаленному репозиторию`
git branch -M main `переключился на ветку main`
git add . `Добавляем файлы в стэш`
git commit -m "First commit" `комитим изменения`
git push -u origin main `Загружаем в удаленный репозиторий`
Для дэплоя на Vercel нужно создать аккаунт и войти в github, после этого импортировать репозиторий, созданный ранее. 

После этого все должно работать.
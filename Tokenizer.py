import torch
from transformers import AutoModel, AutoTokenizer

# 1. Загружаем модель и токенизатор
model_id = "Qwen/Qwen3-Embedding-0.6B"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModel.from_pretrained(model_id, torch_dtype="auto", device_map="auto")

# 2. Текст, который хотим превратить в вектор
text = "Привет, мир!"

# 3. Токенизация
inputs = tokenizer(text, return_tensors="pt")

# 4. Прогон через модель
with torch.no_grad():
    outputs = model(**inputs)

# 5. Берём эмбеддинг (обычно усредняют по всем токенам)
embeddings = outputs.last_hidden_state.mean(dim=1)

print(embeddings.shape)  # например: torch.Size([1, 768])
print(embeddings)        # сам вектор

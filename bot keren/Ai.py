import sys
import argparse
import requests
 
 
OLLAMA_URL = "http://localhost:11434/api/chat"
 
SYSTEM_PROMPT = (
    "Kamu adalah asisten AI yang ramah, santai, dan komunikatif seperti ngobrol "
    "dengan teman. Jawab dalam Bahasa Indonesia sehari-hari yang natural, tidak "
    "kaku atau terlalu formal. Kalau ada sapaan singkat seperti 'oi', 'hai', 'halo', "
    "balas dengan santai juga, jangan dianggap sebagai pertanyaan yang butuh data. "
    "Kalau kamu diberi hasil pencarian web di pesan, gunakan itu sebagai referensi "
    "tambahan dan sebutkan sumbernya secara natural dalam kalimat, jangan kaku."
    "jadi sahabat yang asik, santai, dan komunikatif. Jangan terlalu panjang, cukup ringkas dan jelas."
    "keren dan berkarisma,anggap semua orang yang kamu ajak ngobrol adalah temanmu, jangan terlalu formal."
    "jadi pendegar yang baik."
)
 
 
def search_duckduckgo(query, max_results=5):
    from duckduckgo_search import DDGS
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", "")
            })
    return results
 
 
def search_google(query, max_results=5):
    from googlesearch import search as gsearch
    results = []
    for item in gsearch(query, num_results=max_results, advanced=True):
        results.append({
            "title": getattr(item, "title", str(item)),
            "url": getattr(item, "url", str(item)),
            "snippet": getattr(item, "description", "")
        })
    return results
 
 
def web_search(query, engine="duckduckgo", max_results=5):
    if engine == "google":
        try:
            return search_google(query, max_results)
        except Exception as e:
            print(f"[Google search gagal: {e} -> fallback ke DuckDuckGo]")
            return search_duckduckgo(query, max_results)
    return search_duckduckgo(query, max_results)
 
 
def format_search_results(results):
    if not results:
        return "Tidak ada hasil pencarian."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}\n   URL: {r['url']}\n   {r.get('snippet', '')}")
    return "\n".join(lines)
 
 
SEARCH_TRIGGERS = [
    "terbaru", "sekarang hari ini", "berita", "harga", "kapan tanggal",
    "siapa presiden", "cuaca", "skor pertandingan", "versi terbaru", "tahun ini"
]
 
def needs_search(text):
    t = text.lower().strip()
    if len(t) <= 5:
        return False
    return any(k in t for k in SEARCH_TRIGGERS)
 
 
def call_ollama(model, messages):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]
 
 
 
def main():
    parser = argparse.ArgumentParser(description="AI Terminal Offline dengan Ollama + Web Search")
    parser.add_argument("--model", default="llama3.2", help="Nama model Ollama (default: llama3.2)")
    parser.add_argument("--engine", choices=["duckduckgo", "google"], default="duckduckgo",
                         help="Mesin pencari default")
    args = parser.parse_args()
 
    try:
        requests.get("http://localhost:11434", timeout=3)
    except requests.exceptions.ConnectionError:
        print("Ollama server belum jalan. Pastikan Ollama aktif dulu.")
        sys.exit(1)
 
    model = args.model
    engine = args.engine
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
 
    print("=== AI Terminal Assistant (Ollama - Offline & Gratis) ===")
    print(f"Model              : {model}")
    print(f"Search engine aktif: {engine}")
    print("Perintah: /engine google | /engine duckduckgo | /search <query> | /model <nama> | /exit")
    print()
 
    while True:
        try:
            user_input = input("Kamu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSampai jumpa!")
            break
 
        if not user_input:
            continue
        if user_input == "/exit":
            print("Sampai jumpa!")
            break
 
        if user_input.startswith("/engine"):
            parts = user_input.split(" ", 1)
            if len(parts) == 2 and parts[1].strip() in ("google", "duckduckgo"):
                engine = parts[1].strip()
                print(f"[Search engine diganti ke: {engine}]\n")
            else:
                print("[Gunakan: /engine google  atau  /engine duckduckgo]\n")
            continue
 
        if user_input.startswith("/model"):
            parts = user_input.split(" ", 1)
            if len(parts) == 2 and parts[1].strip():
                model = parts[1].strip()
                print(f"[Model diganti ke: {model}]\n")
            else:
                print("[Gunakan: /model <nama-model>, misal: /model llama3.1]\n")
            continue
 
        if user_input.startswith("/search "):
            query = user_input.split(" ", 1)[1]
            print(f"[Mencari '{query}' via {engine}...]")
            results = web_search(query, engine=engine)
            print(format_search_results(results))
            print()
            continue
 
        if needs_search(user_input):
            print(f"[Info ini mungkin butuh data terkini, mencari via {engine}...]")
            results = web_search(user_input, engine=engine)
            context = "Hasil pencarian web terbaru:\n" + format_search_results(results) + "\n\n"
            final_message = context + f"Pertanyaan: {user_input}"
        else:
            final_message = user_input
 
        history.append({"role": "user", "content": final_message})
 
        try:
            answer = call_ollama(model, history)
        except requests.exceptions.ConnectionError:
            print("[Ollama server tidak bisa dihubungi. Pastikan Ollama masih jalan.]\n")
            history.pop()
            continue
        except Exception as e:
            print(f"[Error memanggil Ollama: {e}]\n")
            history.pop()
            continue
 
        print(f"AI: {answer}\n")

        history[-1] = {"role": "user", "content": user_input}
        history.append({"role": "assistant", "content": answer})
 
 
if __name__ == "__main__":
 main()
import os
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.text import Text

console = Console()

load_dotenv()

from src.document_processor import DocumentProcessor
from src.vector_store import VectorStoreManager
from src.agents.graph import WorkflowManager

def load_pdf_to_db(pdf_path):
    """PDF dosyasını okuyup vektör veritabanına ekleyen yardımcı fonksiyon."""
    if not os.path.exists(pdf_path):
        console.print(f"[bold red]❌ Hata:[/bold red] Belirtilen PDF dosyası bulunamadı: {pdf_path}")
        return False
        
    console.print(f"\n[bold cyan]📄 PDF İşlemi Başlıyor:[/bold cyan] {pdf_path}")
    processor = DocumentProcessor()
    pages = processor.process_pdf(pdf_path)
    
    if pages:
        chunks = processor.chunk_documents(pages)
        vector_store = VectorStoreManager()
        vector_store.delete_collection()
        vector_store.add_documents(chunks)
        console.print("[bold green]✅ PDF başarıyla vektör veritabanına işlendi.[/bold green]")
        return True
    return False

def list_and_select_pdf():
    """Data klasöründeki PDF'leri listeler ve kullanıcıdan menü aracılığıyla seçim alır."""
    data_dir = "data"
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        console.print("[bold yellow]⚠️ 'data' klasörü bulunamadı ve otomatik oluşturuldu. Lütfen içine PDF dosyaları ekleyin.[/bold yellow]")
        return None
        
    pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        console.print("[bold yellow]⚠️ 'data' klasöründe hiç PDF dosyası bulunamadı. Lütfen klasöre dosya ekleyin.[/bold yellow]")
        return None
        
    console.print("\n[bold magenta]📂 Mevcut PDF Dosyaları:[/bold magenta]")
    for i, file in enumerate(pdf_files, 1):
        console.print(f"  [cyan]{i})[/cyan] {file}")
        
    while True:
        choice = Prompt.ask("\n[bold green]Lütfen bir numara seçin[/bold green] (İptal için 'q')").strip()
        
        if choice.lower() in ['q', 'quit', 'iptal']:
            console.print("[yellow]Seçim iptal edildi.[/yellow]")
            return None
            
        try:
            index = int(choice) - 1
            if 0 <= index < len(pdf_files):
                selected_file = os.path.join(data_dir, pdf_files[index])
                return selected_file
            else:
                console.print("[bold red]⚠️ Geçersiz numara. Lütfen listedeki numaralardan birini girin.[/bold red]")
        except ValueError:
            console.print("[bold red]⚠️ Lütfen sadece geçerli bir sayı girin.[/bold red]")

def interactive_loop(workflow_manager):
    console.rule("[bold blue]🤖 Agentic PDF Extractor - İnteraktif Mod[/bold blue]")
    console.print("[dim]💡 Çıkmak için '/q' yazın.[/dim]")
    console.print("[dim]💡 PDF seçmek ve değiştirmek için '/pdf' yazın.[/dim]")
    console.rule()
    
    session_id = "cu_session_1"
    
    while True:
        try:
            # Kullanıcıdan input alma
            user_input = Prompt.ask("\n[bold green]Sen[/bold green]").strip()
            
            if not user_input: continue
                
            if user_input.lower() in ['/q', '/exit', 'quit', 'exit']:
                console.print("\n[bold blue]👋 Sistemden çıkılıyor. Görüşmek üzere![/bold blue]")
                break
                
            if user_input.lower().startswith('/pdf'):
                parts = user_input.split(" ", 1)
                if len(parts) > 1:
                    load_pdf_to_db(parts[1])
                else:
                    selected_pdf = list_and_select_pdf()
                    if selected_pdf:
                        load_pdf_to_db(selected_pdf)
                continue
                
            console.print("\n[dim italic]Sistem düşünüyor ve adımları planlıyor...[/dim italic]")
            
            # Agentları çalıştıran kod
            final_state = workflow_manager.run(question=user_input, thread_id=session_id)
            
            # Gelen cevabı markdown'a çevirip panele ekle
            answer_text = final_state.get("draft_answer", "Cevap üretilemedi.")
            md_answer = Markdown(answer_text)
            
            console.print("\n")
            console.print(Panel(md_answer, title="🎯 [bold magenta]Sistem Yanıtı[/bold magenta]", border_style="magenta", expand=False))
            
        except KeyboardInterrupt:
            console.print("\n[bold blue]👋 Sistemden çıkılıyor...[/bold blue]")
            break
        except Exception as e:
            console.print(f"\n[bold red]❌ Beklenmeyen bir hata oluştu:[/bold red] {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Agentic Bilgi Çıkarımı Sistemi")
    parser.add_argument("--pdf", type=str, help="İşlenecek PDF dosyasının yolu")
    parser.add_argument("--query", type=str, help="Sisteme sorulacak soru")
    
    args = parser.parse_args()
    workflow_manager = WorkflowManager()

    if args.query:
        if args.pdf:
            load_pdf_to_db(args.pdf)
            console.rule()
            
        final_state = workflow_manager.run(question=args.query)
        
        answer_text = final_state.get("draft_answer", "Cevap üretilemedi.")
        md_answer = Markdown(answer_text)
        
        console.print("\n")
        console.print(Panel(md_answer, title="🎯 [bold magenta]Sistem Yanıtı[/bold magenta]", border_style="magenta", expand=False))
        
    else:
        if args.pdf:
            load_pdf_to_db(args.pdf)
        
        interactive_loop(workflow_manager)

if __name__ == "__main__":
    main()
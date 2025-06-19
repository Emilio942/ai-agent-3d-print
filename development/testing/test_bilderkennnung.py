#!/usr/bin/env python3
"""
Bild-Erkennung Deep-Dive Test Suite
Testet die Image-to-3D Pipeline mit verschiedenen Bildtypen
"""

import os
import time
import requests
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import base64

class BildErkennungTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
        self.test_images_dir = "test_images"
        
    def create_test_images(self):
        """Erstelle verschiedene Test-Bilder programmatisch"""
        os.makedirs(self.test_images_dir, exist_ok=True)
        
        try:
            from PIL import Image, ImageDraw
            import numpy as np
            
            # 1. Einfache geometrische Formen
            self.create_simple_shapes()
            
            # 2. Komplexe Formen
            self.create_complex_shapes()
            
            # 3. Text-basierte Bilder
            self.create_text_images()
            
            print(f"✅ Test-Bilder erstellt in {self.test_images_dir}/")
            
        except ImportError:
            print("⚠️ PIL nicht verfügbar - verwende vorhandene Bilder")
    
    def create_simple_shapes(self):
        """Erstelle einfache geometrische Formen"""
        from PIL import Image, ImageDraw
        
        shapes = [
            ("kreis", self.draw_circle),
            ("quadrat", self.draw_square),
            ("dreieck", self.draw_triangle),
            ("stern", self.draw_star),
            ("herz", self.draw_heart)
        ]
        
        for name, draw_func in shapes:
            img = Image.new('RGB', (200, 200), 'white')
            draw = ImageDraw.Draw(img)
            draw_func(draw)
            img.save(f"{self.test_images_dir}/{name}.png")
    
    def draw_circle(self, draw):
        draw.ellipse([50, 50, 150, 150], fill='black')
    
    def draw_square(self, draw):
        draw.rectangle([50, 50, 150, 150], fill='black')
    
    def draw_triangle(self, draw):
        draw.polygon([(100, 50), (50, 150), (150, 150)], fill='black')
    
    def draw_star(self, draw):
        points = []
        center = (100, 100)
        outer_radius = 50
        inner_radius = 25
        
        for i in range(10):
            angle = i * 36  # 360/10
            if i % 2 == 0:
                radius = outer_radius
            else:
                radius = inner_radius
            
            import math
            x = center[0] + radius * math.cos(math.radians(angle - 90))
            y = center[1] + radius * math.sin(math.radians(angle - 90))
            points.append((x, y))
        
        draw.polygon(points, fill='black')
    
    def draw_heart(self, draw):
        # Vereinfachtes Herz
        draw.ellipse([60, 60, 100, 100], fill='black')
        draw.ellipse([100, 60, 140, 100], fill='black')
        draw.polygon([(70, 100), (100, 140), (130, 100)], fill='black')
    
    def create_complex_shapes(self):
        """Erstelle komplexere Formen"""
        from PIL import Image, ImageDraw
        
        # Zahnrad
        img = Image.new('RGB', (200, 200), 'white')
        draw = ImageDraw.Draw(img)
        
        # Äußerer Kreis
        draw.ellipse([40, 40, 160, 160], outline='black', width=3)
        
        # Zähne
        import math
        center = (100, 100)
        for i in range(12):
            angle = i * 30
            x1 = center[0] + 80 * math.cos(math.radians(angle))
            y1 = center[1] + 80 * math.sin(math.radians(angle))
            x2 = center[0] + 90 * math.cos(math.radians(angle))
            y2 = center[1] + 90 * math.sin(math.radians(angle))
            draw.line([(x1, y1), (x2, y2)], fill='black', width=2)
        
        # Innerer Kreis
        draw.ellipse([80, 80, 120, 120], fill='white', outline='black', width=2)
        
        img.save(f"{self.test_images_dir}/zahnrad.png")
    
    def create_text_images(self):
        """Erstelle Text-basierte Bilder"""
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new('RGB', (300, 100), 'white')
        draw = ImageDraw.Draw(img)
        
        try:
            # Versuche eine Systemschrift zu laden
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 30), "TEST", fill='black', font=font)
        img.save(f"{self.test_images_dir}/text_test.png")
    
    def get_test_images(self) -> List[str]:
        """Hole alle verfügbaren Test-Bilder"""
        image_files = []
        
        # Suche in test_images Verzeichnis
        if os.path.exists(self.test_images_dir):
            for file in os.listdir(self.test_images_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_files.append(os.path.join(self.test_images_dir, file))
        
        # Suche im Hauptverzeichnis
        for file in os.listdir('.'):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')) and 'test' in file.lower():
                image_files.append(file)
        
        return image_files
    
    async def teste_bild(self, image_path: str, test_id: int) -> Dict:
        """Teste ein einzelnes Bild"""
        image_name = os.path.basename(image_path)
        print(f"[{test_id:02d}] Teste Bild: '{image_name}'...")
        
        start_time = time.time()
        
        try:
            # Überprüfe ob Datei existiert
            if not os.path.exists(image_path):
                raise Exception(f"Bilddatei nicht gefunden: {image_path}")
            
            # API Request für Image-to-3D
            with open(image_path, 'rb') as f:
                files = {'file': (image_name, f, 'image/png')}
                data = {
                    'style': 'realistic',
                    'quality': 'medium',
                    'extrusion_height': '5.0',
                    'base_thickness': '1.0'
                }
                
                response = requests.post(
                    f"{self.base_url}/api/advanced/image-to-3d/convert",
                    files=files,
                    data=data,
                    timeout=60
                )
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            result_data = response.json()
            
            if not result_data.get("success"):
                raise Exception("API returned success=false")
            
            end_time = time.time()
            
            result = {
                "image_path": image_path,
                "image_name": image_name,
                "success": True,
                "processing_time": end_time - start_time,
                "model_id": result_data.get("model_id"),
                "model_path": result_data.get("model_path"),
                "vertices": result_data.get("metadata", {}).get("vertices"),
                "faces": result_data.get("metadata", {}).get("faces"),
                "file_size": result_data.get("metadata", {}).get("file_size"),
                "error": None
            }
            
            print(f"  ✅ Erfolgreich in {result['processing_time']:.1f}s")
            print(f"     Model: {result['vertices']} vertices, {result['faces']} faces")
            return result
            
        except Exception as e:
            end_time = time.time()
            result = {
                "image_path": image_path,
                "image_name": image_name,
                "success": False,
                "processing_time": end_time - start_time,
                "model_id": None,
                "model_path": None,
                "vertices": None,
                "faces": None,
                "file_size": None,
                "error": str(e)
            }
            
            print(f"  ❌ Fehlgeschlagen: {e}")
            return result
    
    async def teste_image_to_print_workflow(self, image_path: str) -> Dict:
        """Teste den vollständigen Image-to-Print Workflow"""
        image_name = os.path.basename(image_path)
        print(f"🖨️ Teste Image-to-Print Workflow: '{image_name}'...")
        
        start_time = time.time()
        
        try:
            # API Request für Image-Print
            with open(image_path, 'rb') as f:
                files = {'image': (image_name, f, 'image/png')}
                data = {
                    'extrusion_height': '3.0',
                    'base_thickness': '0.5',
                    'priority': 'normal'
                }
                
                response = requests.post(
                    f"{self.base_url}/api/image-print-request",
                    files=files,
                    data=data,
                    timeout=30
                )
            
            if response.status_code != 201:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            job_data = response.json()
            job_id = job_data["job_id"]
            
            # Warte auf Completion
            for i in range(120):  # 2 Minuten timeout
                status_response = requests.get(f"{self.base_url}/api/status/{job_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data["status"] == "completed":
                        end_time = time.time()
                        
                        return {
                            "image_path": image_path,
                            "image_name": image_name,
                            "success": True,
                            "job_id": job_id,
                            "processing_time": end_time - start_time,
                            "output_files": status_data.get("output_files"),
                            "error": None
                        }
                        
                    elif status_data["status"] in ["failed", "cancelled"]:
                        raise Exception(f"Workflow failed: {status_data.get('error_message', 'Unknown error')}")
                
                time.sleep(1)
            
            raise Exception("Timeout nach 2 Minuten")
            
        except Exception as e:
            end_time = time.time()
            return {
                "image_path": image_path,
                "image_name": image_name,
                "success": False,
                "job_id": None,
                "processing_time": end_time - start_time,
                "output_files": None,
                "error": str(e)
            }
    
    async def deep_dive_test(self):
        """Führe Deep-Dive Test durch"""
        print("🔬 Starte Bild-Erkennung Deep-Dive Test...")
        
        # Erstelle Test-Bilder
        self.create_test_images()
        
        # Hole alle verfügbaren Bilder
        test_images = self.get_test_images()
        
        if not test_images:
            print("❌ Keine Test-Bilder gefunden!")
            return
        
        print(f"📷 Gefundene Test-Bilder: {len(test_images)}")
        for img in test_images:
            print(f"  • {img}")
        
        start_time = datetime.now()
        
        # Test 1: Image-to-3D Conversion
        print("\n🧪 Test 1: Image-to-3D Conversion")
        conversion_results = {}
        for i, image_path in enumerate(test_images, 1):
            result = await self.teste_bild(image_path, i)
            conversion_results[image_path] = result
        
        # Test 2: Image-to-Print Workflow (nur mit ersten 3 Bildern)
        print("\n🧪 Test 2: Image-to-Print Workflow")
        workflow_results = {}
        for i, image_path in enumerate(test_images[:3], 1):
            result = await self.teste_image_to_print_workflow(image_path)
            workflow_results[image_path] = result
        
        end_time = datetime.now()
        
        # Report generieren
        self.generate_image_report(conversion_results, workflow_results, start_time, end_time)
    
    def generate_image_report(self, conversion_results, workflow_results, start_time, end_time):
        """Generiere Bild-Test Report"""
        total_time = (end_time - start_time).total_seconds()
        
        print("\n" + "="*80)
        print("🔬 BILD-ERKENNUNG DEEP-DIVE REPORT")
        print("="*80)
        print(f"📅 Start: {start_time.strftime('%H:%M:%S')}")
        print(f"📅 Ende: {end_time.strftime('%H:%M:%S')}")
        print(f"⏱️ Gesamtzeit: {total_time:.1f} Sekunden")
        
        # Conversion Results
        successful_conversions = sum(1 for r in conversion_results.values() if r["success"])
        conversion_rate = (successful_conversions / len(conversion_results)) * 100
        
        print(f"\n📷 IMAGE-TO-3D CONVERSION:")
        print(f"✅ Erfolgreich: {successful_conversions}/{len(conversion_results)} ({conversion_rate:.1f}%)")
        
        if successful_conversions > 0:
            successful_times = [r["processing_time"] for r in conversion_results.values() if r["success"]]
            avg_time = sum(successful_times) / len(successful_times)
            print(f"⚡ Durchschnittliche Zeit: {avg_time:.2f}s")
            
            # Modell-Komplexität
            vertices_data = [r["vertices"] for r in conversion_results.values() if r["success"] and r["vertices"]]
            if vertices_data:
                avg_vertices = sum(vertices_data) / len(vertices_data)
                print(f"🔺 Durchschnittliche Vertices: {avg_vertices:.0f}")
        
        # Workflow Results
        if workflow_results:
            successful_workflows = sum(1 for r in workflow_results.values() if r["success"])
            workflow_rate = (successful_workflows / len(workflow_results)) * 100
            
            print(f"\n🖨️ IMAGE-TO-PRINT WORKFLOW:")
            print(f"✅ Erfolgreich: {successful_workflows}/{len(workflow_results)} ({workflow_rate:.1f}%)")
        
        # Fehlgeschlagene Bilder
        failed_conversions = [name for name, r in conversion_results.items() if not r["success"]]
        if failed_conversions:
            print(f"\n❌ FEHLGESCHLAGENE CONVERSIONS:")
            for name in failed_conversions:
                error = conversion_results[name]["error"]
                print(f"  • {os.path.basename(name)}: {error}")
        
        # Speichere Report
        report_file = f"image_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "meta": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "total_time_seconds": total_time
                },
                "conversion_results": conversion_results,
                "workflow_results": workflow_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detaillierter Report gespeichert: {report_file}")
        print("="*80)


async def main():
    """Hauptfunktion"""
    tester = BildErkennungTester()
    
    # Teste Server-Verbindung
    try:
        response = requests.get(f"{tester.base_url}/health", timeout=5)
        if response.status_code != 200:
            raise Exception("Server nicht erreichbar")
        print("✅ Server-Verbindung erfolgreich")
    except Exception as e:
        print(f"❌ Server-Verbindung fehlgeschlagen: {e}")
        return
    
    await tester.deep_dive_test()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

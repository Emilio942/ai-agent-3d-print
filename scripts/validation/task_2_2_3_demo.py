#!/usr/bin/env python3
"""
Task 2.2.3: STL Export with Quality Control - Demonstration Script

This script demonstrates the complete STL export functionality implemented for Task 2.2.3,
showcasing quality control, mesh optimization, and validation features.
"""

import asyncio
import os
import sys
import tempfile
import time

# Add path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.cad_agent import CADAgent


async def demo_stl_export_with_quality_control():
    """Demonstrate STL export with comprehensive quality control."""
    print("="*70)
    print("🔧 STL EXPORT WITH QUALITY CONTROL DEMONSTRATION")
    print("="*70)
    
    agent = CADAgent("stl_export_demo")
    
    try:
        temp_dir = tempfile.mkdtemp()
        print(f"📁 Working directory: {temp_dir}")
        
        # Step 1: Create a complex primitive
        print("\n🎯 Step 1: Creating Complex Primitive")
        print("-" * 40)
        
        primitive_task = {
            'operation': 'create_primitive',
            'specifications': {
                'geometry': {
                    'base_shape': 'torus',
                    'dimensions': {
                        'major_radius': 20,
                        'minor_radius': 5
                    }
                }
            },
            'requirements': {},
            'format_preference': 'stl',
            'quality_level': 'high'
        }
        
        start_time = time.time()
        primitive_result = await agent.execute_task(primitive_task)
        primitive_time = time.time() - start_time
        
        if primitive_result.success:
            print(f"✅ Torus created successfully in {primitive_time:.2f}s")
            print(f"   📐 Volume: {primitive_result.data.get('volume', 0):.2f} mm³")
            print(f"   📏 Complexity: {primitive_result.data.get('complexity_metrics', {}).get('geometric_complexity', 0)}/10")
            print(f"   🎨 Quality: {primitive_result.data.get('quality_score', 0)}/10")
            print(f"   📊 Printability: {primitive_result.data.get('printability_score', 0)}/10")
        else:
            print(f"❌ Primitive creation failed: {primitive_result.error_message}")
            return
        
        source_file = primitive_result.data['model_file_path']
        print(f"   📄 Source file: {source_file}")
        
        # Step 2: Export with different quality levels
        print("\n🔍 Step 2: STL Export with Different Quality Levels")
        print("-" * 55)
        
        quality_levels = [
            ("draft", "Fast processing with aggressive optimization"),
            ("standard", "Balanced quality and performance"),
            ("high", "Maximum quality with minimal optimization"),
            ("ultra", "Pristine quality preservation")
        ]
        
        export_results = {}
        
        for quality, description in quality_levels:
            print(f"\n📤 Exporting with '{quality}' quality level...")
            print(f"   💡 {description}")
            
            output_file = os.path.join(temp_dir, f"torus_{quality}.stl")
            
            export_task = {
                'operation': 'export_stl',
                'specifications': {
                    'stl_export': {
                        'source_file_path': source_file,
                        'output_file_path': output_file,
                        'quality_level': quality,
                        'perform_quality_check': True,
                        'auto_repair_issues': True,
                        'generate_report': True,
                        'export_options': {
                            'mesh_resolution': 0.05 if quality == 'draft' else 0.1,
                            'optimize_mesh': True,
                            'validate_manifold': True,
                            'auto_repair': True,
                            'include_normals': True
                        }
                    }
                },
                'requirements': {},
                'format_preference': 'stl',
                'quality_level': quality
            }
            
            start_time = time.time()
            export_result = await agent.execute_task(export_task)
            export_time = time.time() - start_time
            
            if export_result.success:
                data = export_result.data
                file_size_kb = data.get('file_size_bytes', 0) / 1024
                compression = data.get('compression_ratio', 0) * 100
                quality_score = data.get('mesh_quality_report', {}).get('quality_score', 0)
                printability = data.get('printability_assessment', {}).get('score', 0)
                repairs = len(data.get('repairs_applied', []))
                warnings = len(data.get('warnings', []))
                
                export_results[quality] = {
                    'success': True,
                    'file_size_kb': file_size_kb,
                    'compression': compression,
                    'quality_score': quality_score,
                    'printability': printability,
                    'repairs': repairs,
                    'warnings': warnings,
                    'export_time': export_time
                }
                
                print(f"   ✅ Export successful in {export_time:.2f}s")
                print(f"   📁 File size: {file_size_kb:.1f} KB")
                print(f"   🗜️  Compression: {compression:.1f}%")
                print(f"   🎨 Quality score: {quality_score:.1f}/10")
                print(f"   📊 Printability: {printability:.1f}/10")
                print(f"   🔧 Repairs applied: {repairs}")
                print(f"   ⚠️  Warnings: {warnings}")
                
            else:
                export_results[quality] = {
                    'success': False,
                    'error': export_result.error_message
                }
                print(f"   ❌ Export failed: {export_result.error_message}")
        
        # Step 3: Detailed quality analysis
        print("\n🔬 Step 3: Detailed Quality Analysis")
        print("-" * 40)
        
        # Use the 'high' quality export for detailed analysis
        if 'high' in export_results and export_results['high']['success']:
            high_quality_file = os.path.join(temp_dir, "torus_high.stl")
            
            # Demonstrate quality analysis functions
            print("🧪 Running comprehensive quality analysis...")
            
            # Load the exported mesh for analysis
            try:
                mesh = agent._load_mesh_from_file(high_quality_file)
                
                # Generate detailed quality report
                quality_report = agent._generate_mesh_quality_report(mesh)
                
                print(f"\n📋 Mesh Quality Report:")
                print(f"   🔍 Manifold: {'✅ Yes' if quality_report.get('is_manifold') else '❌ No'}")
                print(f"   💧 Watertight: {'✅ Yes' if quality_report.get('is_watertight') else '❌ No'}")
                print(f"   ⚠️  Degenerate faces: {'❌ Yes' if quality_report.get('has_degenerate_faces') else '✅ No'}")
                print(f"   📊 Vertices: {quality_report.get('vertex_count', 0):,}")
                print(f"   🔺 Faces: {quality_report.get('face_count', 0):,}")
                print(f"   📐 Volume: {quality_report.get('volume', 0):.2f} mm³")
                print(f"   📏 Surface area: {quality_report.get('surface_area', 0):.2f} mm²")
                print(f"   🎯 Overall score: {quality_report.get('quality_score', 0):.1f}/10")
                
                issues = quality_report.get('issues', [])
                recommendations = quality_report.get('recommendations', [])
                
                if issues:
                    print(f"\n⚠️  Issues detected ({len(issues)}):")
                    for i, issue in enumerate(issues[:3], 1):  # Show first 3
                        print(f"   {i}. {issue}")
                    if len(issues) > 3:
                        print(f"   ... and {len(issues) - 3} more")
                
                if recommendations:
                    print(f"\n💡 Recommendations ({len(recommendations)}):")
                    for i, rec in enumerate(recommendations[:3], 1):  # Show first 3
                        print(f"   {i}. {rec}")
                    if len(recommendations) > 3:
                        print(f"   ... and {len(recommendations) - 3} more")
                
                # STL validation
                print(f"\n🔍 STL File Validation:")
                stl_validation = agent._validate_stl_file(high_quality_file)
                
                print(f"   📄 Valid STL: {'✅ Yes' if stl_validation.get('is_valid_stl') else '❌ No'}")
                print(f"   📊 Triangle count: {stl_validation.get('triangle_count', 0):,}")
                print(f"   📁 File size: {stl_validation.get('file_size_mb', 0):.2f} MB")
                print(f"   📝 Format: {'ASCII' if stl_validation.get('is_ascii_format') else 'Binary'}")
                
                format_errors = stl_validation.get('format_errors', [])
                if format_errors:
                    print(f"   ❌ Format errors: {len(format_errors)}")
                    for error in format_errors[:2]:
                        print(f"      • {error}")
                
                # Printability assessment
                print(f"\n🖨️  Printability Assessment:")
                printability = agent._assess_stl_printability(mesh, high_quality_file)
                
                print(f"   🎯 Printability score: {printability.get('score', 0):.1f}/10")
                print(f"   🏗️  Support needed: {'✅ Yes' if printability.get('support_needed') else '❌ No'}")
                print(f"   ⏱️  Est. print time: {printability.get('estimated_print_time', 0)} minutes")
                
                print_issues = printability.get('issues', [])
                if print_issues:
                    print(f"   ⚠️  Print issues ({len(print_issues)}):")
                    for issue in print_issues[:2]:
                        print(f"      • {issue}")
                
            except Exception as e:
                print(f"   ❌ Quality analysis failed: {e}")
        
        # Step 4: Export comparison summary
        print("\n📊 Step 4: Export Quality Comparison")
        print("-" * 40)
        
        successful_exports = {k: v for k, v in export_results.items() if v.get('success')}
        
        if successful_exports:
            print(f"📈 Successfully exported {len(successful_exports)}/{len(quality_levels)} quality levels\n")
            
            # Create comparison table
            print(f"{'Quality':<10} {'Size (KB)':<10} {'Quality':<10} {'Print':<10} {'Time (s)':<10}")
            print("-" * 55)
            
            for quality in ['draft', 'standard', 'high', 'ultra']:
                if quality in successful_exports:
                    data = successful_exports[quality]
                    print(f"{quality:<10} "
                          f"{data['file_size_kb']:<10.1f} "
                          f"{data['quality_score']:<10.1f} "
                          f"{data['printability']:<10.1f} "
                          f"{data['export_time']:<10.2f}")
            
            # Best recommendations
            print(f"\n🏆 Recommendations:")
            
            # Find best quality
            best_quality = max(successful_exports.items(), 
                             key=lambda x: x[1]['quality_score'])
            print(f"   🎨 Best quality: {best_quality[0]} ({best_quality[1]['quality_score']:.1f}/10)")
            
            # Find best printability
            best_printability = max(successful_exports.items(), 
                                  key=lambda x: x[1]['printability'])
            print(f"   🖨️  Best printability: {best_printability[0]} ({best_printability[1]['printability']:.1f}/10)")
            
            # Find smallest file
            smallest_file = min(successful_exports.items(), 
                              key=lambda x: x[1]['file_size_kb'])
            print(f"   📁 Smallest file: {smallest_file[0]} ({smallest_file[1]['file_size_kb']:.1f} KB)")
            
            # Find fastest export
            fastest_export = min(successful_exports.items(), 
                                key=lambda x: x[1]['export_time'])
            print(f"   ⚡ Fastest export: {fastest_export[0]} ({fastest_export[1]['export_time']:.2f}s)")
        
        # Cleanup
        print(f"\n🧹 Cleaning up temporary files...")
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        agent.cleanup()
        
        print("\n🎉 STL Export Quality Control Demonstration Complete!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


def show_feature_summary():
    """Show summary of implemented Task 2.2.3 features."""
    print("\n📋 TASK 2.2.3: STL Export with Quality Control - Feature Summary")
    print("="*70)
    
    features = [
        ("🔍 Mesh Validation", [
            "Manifold geometry checking",
            "Watertight boundary verification", 
            "Degenerate face detection",
            "Duplicate vertex/face identification",
            "Boundary edge analysis"
        ]),
        
        ("🛠️  Automatic Repair", [
            "Hole filling and boundary closure",
            "Duplicate removal and cleanup",
            "Normal vector correction",
            "Manifold structure repair",
            "Degenerate geometry removal"
        ]),
        
        ("📊 Quality Control", [
            "Comprehensive quality scoring (0-10)",
            "Detailed mesh analysis reports",
            "Printability assessment",
            "Issue identification and recommendations",
            "Multi-level quality validation"
        ]),
        
        ("🗜️  File Optimization", [
            "Quality-based mesh optimization",
            "Resolution adjustment controls",
            "File size reduction algorithms",
            "Configurable compression levels",
            "Performance vs quality balancing"
        ]),
        
        ("📤 Export Options", [
            "Binary/ASCII STL format support",
            "Normal vector inclusion control",
            "Configurable mesh resolution",
            "Multiple quality level presets",
            "Batch processing capabilities"
        ]),
        
        ("🔌 Integration", [
            "Seamless primitive creation workflow",
            "Boolean operation result export",
            "API schema validation",
            "Error handling and recovery",
            "Comprehensive logging and reporting"
        ])
    ]
    
    for category, items in features:
        print(f"\n{category}")
        print("-" * (len(category) - 2))  # Subtract emoji chars
        for item in items:
            print(f"   ✅ {item}")
    
    print(f"\n🎯 Implementation Status: Complete")
    print(f"📈 Quality Assurance: Comprehensive test suite included")
    print(f"🔗 Integration: Full workflow compatibility")
    print("="*70)


if __name__ == "__main__":
    print("🚀 Starting STL Export Quality Control Demo...")
    
    try:
        # Show feature summary first
        show_feature_summary()
        
        # Run demonstration
        asyncio.run(demo_stl_export_with_quality_control())
        
    except KeyboardInterrupt:
        print("\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n👋 Demo finished. Thank you!")

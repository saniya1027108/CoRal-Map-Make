def call_openai_extraction(client: OpenAI, pdf_path: Path, prompt: str, model: str) -> str:
    """Call OpenAI (GPT-4o) for extraction using Responses API."""
    logger.info(f"📤 Uploading PDF to OpenAI...")
    try:
        with open(pdf_path, 'rb') as f:
            uploaded_file = client.files.create(
                file=f,
                purpose="assistants"
            )
        file_id = uploaded_file.id
        pdf_size_mb = pdf_path.stat().st_size / 1024 / 1024
        logger.info(f"   ✅ PDF uploaded: {file_id} ({pdf_size_mb:.2f} MB)")
    except Exception as e:
        logger.error(f"   ❌ Failed to upload PDF: {e}")
        raise
    
    logger.info(f"🤖 Calling OpenAI {model} for extraction...")
    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_file", "file_id": file_id}
                    ]
                }
            ]
        )
        
        result = response.output_text.strip()
        
        # Clean up uploaded file
        try:
            client.files.delete(file_id)
            logger.info(f"   🗑️  Cleaned up uploaded PDF")
        except:
            pass
        
        return result
        
    except Exception as e:
        logger.error(f"   ❌ OpenAI call failed: {e}")
        # Try cleanup even on error
        try:
            if 'file_id' in locals():
                client.files.delete(file_id)
        except:
            pass
        raise


def call_gemini_extraction(client, pdf_path: Path, prompt: str, model: str) -> str:
    """Call Gemini for extraction using Gemini API."""
    logger.info(f"📤 Loading PDF for Gemini...")
    try:
        pdf_bytes = pdf_path.read_bytes()
        pdf_size_mb = len(pdf_bytes) / 1024 / 1024
        logger.info(f"   ✅ PDF loaded: {pdf_size_mb:.2f} MB")
    except Exception as e:
        logger.error(f"   ❌ Failed to load PDF: {e}")
        raise
    
    # Create PDF part for Gemini
    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    
    logger.info(f"🤖 Calling Gemini {model} for extraction...")
    try:
        config = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=8000
        )
        
        response = client.models.generate_content(
            model=model,
            contents=[pdf_part, prompt],
            config=config
        )
        
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"   ❌ Gemini call failed: {e}")
        raise

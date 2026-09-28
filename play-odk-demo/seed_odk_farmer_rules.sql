BEGIN;

INSERT INTO public.data_models (
  data_model_id, data_model_mnemonic, pattern_for_data_model,
  response_template_document_id, is_active
) VALUES (
  'odk_farmer_v1_data_model',
  'ODK_FARMER_V1',
  '$.body.header.sender_id=>^odk-farmer-play$',
  NULL,
  TRUE
) ON CONFLICT (data_model_id) DO UPDATE SET
  data_model_mnemonic = EXCLUDED.data_model_mnemonic,
  pattern_for_data_model = EXCLUDED.pattern_for_data_model,
  is_active = EXCLUDED.is_active;

INSERT INTO public.incoming_model_key_paths (
  key_path_id, data_model_id,
  key_path_for_message_id, key_path_for_sender,
  key_path_for_signature, key_path_for_signature_payload,
  is_list, key_path_for_list_elements
) VALUES (
  'odk_farmer_v1_key_paths',
  'odk_farmer_v1_data_model',
  '$.body.header.message_id',
  '$.body.header.sender_id',
  '$.body.header.signature',
  '$.body.message',
  FALSE,
  '$.body.message.payload'
) ON CONFLICT (key_path_id) DO UPDATE SET
  data_model_id = EXCLUDED.data_model_id,
  key_path_for_message_id = EXCLUDED.key_path_for_message_id,
  key_path_for_sender = EXCLUDED.key_path_for_sender,
  key_path_for_signature = EXCLUDED.key_path_for_signature,
  key_path_for_signature_payload = EXCLUDED.key_path_for_signature_payload,
  is_list = EXCLUDED.is_list,
  key_path_for_list_elements = EXCLUDED.key_path_for_list_elements;

INSERT INTO public.incoming_model_semantic_patterns (
  semantic_pattern_id, data_model_id, register_id,
  pattern_for_register, key_path_for_business_payload,
  raw_payload_enricher_class, intake_form_id, pattern_for_intake_form
) VALUES (
  'odk_farmer_v1_farmer_pattern',
  'odk_farmer_v1_data_model',
  'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd',
  '$.body.message.payload.register_mnemonic=>^Farmer$',
  '$.body.message.payload',
  'G2PSpdciFarmerCreateEnricherService',
  'a1a4d25a-1cd4-4356-abac-8782382649',
  '$.body.message.payload.register_mnemonic=>^Farmer$'
) ON CONFLICT (semantic_pattern_id) DO UPDATE SET
  data_model_id = EXCLUDED.data_model_id,
  register_id = EXCLUDED.register_id,
  pattern_for_register = EXCLUDED.pattern_for_register,
  key_path_for_business_payload = EXCLUDED.key_path_for_business_payload,
  raw_payload_enricher_class = EXCLUDED.raw_payload_enricher_class,
  intake_form_id = EXCLUDED.intake_form_id,
  pattern_for_intake_form = EXCLUDED.pattern_for_intake_form;

INSERT INTO public.g2p_registry_documents (
  document_id, document_store_id, bucket, source_filename, created_at, created_by
) VALUES (
  'a1111111-1111-4111-8111-111111111111',
  'odk_to_openg2p_farmer.json.j2',
  'templates',
  'odk_to_openg2p_farmer.json.j2',
  NOW(),
  'seeder'
) ON CONFLICT (document_id) DO UPDATE SET
  document_store_id = EXCLUDED.document_store_id,
  bucket = EXCLUDED.bucket,
  source_filename = EXCLUDED.source_filename;

INSERT INTO public.incoming_templates (
  template_id, register_id, data_model_id, template_document_id,
  jsonld_expansion_required, created_at, updated_at
) VALUES (
  'odk_farmer_v1_template',
  'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd',
  'odk_farmer_v1_data_model',
  'a1111111-1111-4111-8111-111111111111',
  FALSE,
  NOW(),
  NULL
) ON CONFLICT (template_id) DO UPDATE SET
  register_id = EXCLUDED.register_id,
  data_model_id = EXCLUDED.data_model_id,
  template_document_id = EXCLUDED.template_document_id,
  jsonld_expansion_required = EXCLUDED.jsonld_expansion_required,
  updated_at = NOW();

COMMIT;

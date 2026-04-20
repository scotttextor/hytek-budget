import { createClient } from '@supabase/supabase-js'

// Shared HYTEK Supabase (hytek-detailing project).
// Keys hardcoded as fallbacks per hytek-detailing CLAUDE.md convention —
// anon key is public by design (RLS is the security layer), URL is public.
// Env vars take precedence when present (e.g. local dev with .env.local),
// hardcoded values ensure the app builds + runs even if Vercel env var
// wiring has any issue. Matches lib/supabase.ts pattern in hytek-detailing.
const FALLBACK_URL = 'https://gqtikzguvhukpujyxkez.supabase.co'
const FALLBACK_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxdGlremd1dmh1a3B1anl4a2V6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0NTkzMTksImV4cCI6MjA5MTAzNTMxOX0.6fWNYBIw9_2_CcgJq2n5n3hw5E5wwyd5vHdZn1vCE0k'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || FALLBACK_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || FALLBACK_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)


-- bot_conversations
CREATE TABLE public.bot_conversations (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_name TEXT,
  user_email TEXT,
  user_messenger TEXT,
  user_external_id TEXT,
  source TEXT NOT NULL DEFAULT 'site',
  status TEXT NOT NULL DEFAULT 'new',
  lead_id UUID REFERENCES public.leads(id) ON DELETE SET NULL,
  admin_note TEXT,
  first_message_at TIMESTAMPTZ,
  last_message_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.bot_conversations TO authenticated;
GRANT ALL ON public.bot_conversations TO service_role;

ALTER TABLE public.bot_conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admins can view conversations" ON public.bot_conversations
  FOR SELECT TO authenticated USING (public.has_role(auth.uid(), 'admin'));
CREATE POLICY "Admins can insert conversations" ON public.bot_conversations
  FOR INSERT TO authenticated WITH CHECK (public.has_role(auth.uid(), 'admin'));
CREATE POLICY "Admins can update conversations" ON public.bot_conversations
  FOR UPDATE TO authenticated USING (public.has_role(auth.uid(), 'admin'));
CREATE POLICY "Admins can delete conversations" ON public.bot_conversations
  FOR DELETE TO authenticated USING (public.has_role(auth.uid(), 'admin'));

CREATE TRIGGER bot_conversations_set_updated_at
  BEFORE UPDATE ON public.bot_conversations
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE INDEX bot_conversations_last_message_idx ON public.bot_conversations (last_message_at DESC);
CREATE INDEX bot_conversations_lead_idx ON public.bot_conversations (lead_id);

-- bot_messages
CREATE TABLE public.bot_messages (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES public.bot_conversations(id) ON DELETE CASCADE,
  sender_type TEXT NOT NULL CHECK (sender_type IN ('user','bot','admin')),
  message_text TEXT NOT NULL,
  message_channel TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.bot_messages TO authenticated;
GRANT ALL ON public.bot_messages TO service_role;

ALTER TABLE public.bot_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admins can view messages" ON public.bot_messages
  FOR SELECT TO authenticated USING (public.has_role(auth.uid(), 'admin'));
CREATE POLICY "Admins can insert messages" ON public.bot_messages
  FOR INSERT TO authenticated WITH CHECK (public.has_role(auth.uid(), 'admin'));
CREATE POLICY "Admins can update messages" ON public.bot_messages
  FOR UPDATE TO authenticated USING (public.has_role(auth.uid(), 'admin'));
CREATE POLICY "Admins can delete messages" ON public.bot_messages
  FOR DELETE TO authenticated USING (public.has_role(auth.uid(), 'admin'));

CREATE INDEX bot_messages_conversation_idx ON public.bot_messages (conversation_id, created_at);

-- leads.conversation_id
ALTER TABLE public.leads ADD COLUMN conversation_id UUID REFERENCES public.bot_conversations(id) ON DELETE SET NULL;
CREATE INDEX leads_conversation_idx ON public.leads (conversation_id);

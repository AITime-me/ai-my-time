export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      bot_conversations: {
        Row: {
          admin_note: string | null
          created_at: string
          first_message_at: string | null
          id: string
          last_message_at: string | null
          lead_id: string | null
          source: string
          status: string
          updated_at: string
          user_email: string | null
          user_external_id: string | null
          user_messenger: string | null
          user_name: string | null
        }
        Insert: {
          admin_note?: string | null
          created_at?: string
          first_message_at?: string | null
          id?: string
          last_message_at?: string | null
          lead_id?: string | null
          source?: string
          status?: string
          updated_at?: string
          user_email?: string | null
          user_external_id?: string | null
          user_messenger?: string | null
          user_name?: string | null
        }
        Update: {
          admin_note?: string | null
          created_at?: string
          first_message_at?: string | null
          id?: string
          last_message_at?: string | null
          lead_id?: string | null
          source?: string
          status?: string
          updated_at?: string
          user_email?: string | null
          user_external_id?: string | null
          user_messenger?: string | null
          user_name?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "bot_conversations_lead_id_fkey"
            columns: ["lead_id"]
            isOneToOne: false
            referencedRelation: "leads"
            referencedColumns: ["id"]
          },
        ]
      }
      bot_messages: {
        Row: {
          conversation_id: string
          created_at: string
          id: string
          message_channel: string | null
          message_text: string
          metadata: Json | null
          sender_type: string
        }
        Insert: {
          conversation_id: string
          created_at?: string
          id?: string
          message_channel?: string | null
          message_text: string
          metadata?: Json | null
          sender_type: string
        }
        Update: {
          conversation_id?: string
          created_at?: string
          id?: string
          message_channel?: string | null
          message_text?: string
          metadata?: Json | null
          sender_type?: string
        }
        Relationships: [
          {
            foreignKeyName: "bot_messages_conversation_id_fkey"
            columns: ["conversation_id"]
            isOneToOne: false
            referencedRelation: "bot_conversations"
            referencedColumns: ["id"]
          },
        ]
      }
      cases: {
        Row: {
          category: string | null
          created_at: string
          ecosystem_role: string | null
          id: string
          image_url: string | null
          is_active: boolean
          note: string | null
          result: string | null
          seo_description: string | null
          seo_title: string | null
          solution: string | null
          sort_order: number
          status: string | null
          task: string | null
          title: string
          updated_at: string
        }
        Insert: {
          category?: string | null
          created_at?: string
          ecosystem_role?: string | null
          id?: string
          image_url?: string | null
          is_active?: boolean
          note?: string | null
          result?: string | null
          seo_description?: string | null
          seo_title?: string | null
          solution?: string | null
          sort_order?: number
          status?: string | null
          task?: string | null
          title: string
          updated_at?: string
        }
        Update: {
          category?: string | null
          created_at?: string
          ecosystem_role?: string | null
          id?: string
          image_url?: string | null
          is_active?: boolean
          note?: string | null
          result?: string | null
          seo_description?: string | null
          seo_title?: string | null
          solution?: string | null
          sort_order?: number
          status?: string | null
          task?: string | null
          title?: string
          updated_at?: string
        }
        Relationships: []
      }
      faq: {
        Row: {
          answer: string
          category: string | null
          created_at: string
          id: string
          is_active: boolean
          question: string
          sort_order: number
          updated_at: string
        }
        Insert: {
          answer: string
          category?: string | null
          created_at?: string
          id?: string
          is_active?: boolean
          question: string
          sort_order?: number
          updated_at?: string
        }
        Update: {
          answer?: string
          category?: string | null
          created_at?: string
          id?: string
          is_active?: boolean
          question?: string
          sort_order?: number
          updated_at?: string
        }
        Relationships: []
      }
      leads: {
        Row: {
          admin_comment: string | null
          business_area: string | null
          conversation_id: string | null
          created_at: string
          email: string | null
          id: string
          message: string | null
          name: string
          phone_or_telegram: string | null
          source: string | null
          status: string
          task: string | null
        }
        Insert: {
          admin_comment?: string | null
          business_area?: string | null
          conversation_id?: string | null
          created_at?: string
          email?: string | null
          id?: string
          message?: string | null
          name: string
          phone_or_telegram?: string | null
          source?: string | null
          status?: string
          task?: string | null
        }
        Update: {
          admin_comment?: string | null
          business_area?: string | null
          conversation_id?: string | null
          created_at?: string
          email?: string | null
          id?: string
          message?: string | null
          name?: string
          phone_or_telegram?: string | null
          source?: string | null
          status?: string
          task?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "leads_conversation_id_fkey"
            columns: ["conversation_id"]
            isOneToOne: false
            referencedRelation: "bot_conversations"
            referencedColumns: ["id"]
          },
        ]
      }
      legal_pages: {
        Row: {
          content: string
          id: string
          title: string
          type: string
          updated_at: string
        }
        Insert: {
          content: string
          id?: string
          title: string
          type: string
          updated_at?: string
        }
        Update: {
          content?: string
          id?: string
          title?: string
          type?: string
          updated_at?: string
        }
        Relationships: []
      }
      services: {
        Row: {
          audience: string | null
          created_at: string
          cta_text: string | null
          full_description: string | null
          h1: string | null
          id: string
          includes: string | null
          is_active: boolean
          result: string | null
          seo_description: string | null
          seo_title: string | null
          short_description: string | null
          slug: string
          sort_order: number
          title: string
          updated_at: string
        }
        Insert: {
          audience?: string | null
          created_at?: string
          cta_text?: string | null
          full_description?: string | null
          h1?: string | null
          id?: string
          includes?: string | null
          is_active?: boolean
          result?: string | null
          seo_description?: string | null
          seo_title?: string | null
          short_description?: string | null
          slug: string
          sort_order?: number
          title: string
          updated_at?: string
        }
        Update: {
          audience?: string | null
          created_at?: string
          cta_text?: string | null
          full_description?: string | null
          h1?: string | null
          id?: string
          includes?: string | null
          is_active?: boolean
          result?: string | null
          seo_description?: string | null
          seo_title?: string | null
          short_description?: string | null
          slug?: string
          sort_order?: number
          title?: string
          updated_at?: string
        }
        Relationships: []
      }
      site_settings: {
        Row: {
          analytics_enabled: boolean
          bot_link: string | null
          bot_widget_enabled: boolean
          bot_widget_text: string | null
          email: string | null
          google_analytics_id: string | null
          id: number
          main_cta_text: string | null
          og_image: string | null
          phone: string | null
          site_description: string | null
          site_title: string | null
          social_links: Json | null
          telegram: string | null
          updated_at: string
          yandex_metrika_id: string | null
        }
        Insert: {
          analytics_enabled?: boolean
          bot_link?: string | null
          bot_widget_enabled?: boolean
          bot_widget_text?: string | null
          email?: string | null
          google_analytics_id?: string | null
          id?: number
          main_cta_text?: string | null
          og_image?: string | null
          phone?: string | null
          site_description?: string | null
          site_title?: string | null
          social_links?: Json | null
          telegram?: string | null
          updated_at?: string
          yandex_metrika_id?: string | null
        }
        Update: {
          analytics_enabled?: boolean
          bot_link?: string | null
          bot_widget_enabled?: boolean
          bot_widget_text?: string | null
          email?: string | null
          google_analytics_id?: string | null
          id?: number
          main_cta_text?: string | null
          og_image?: string | null
          phone?: string | null
          site_description?: string | null
          site_title?: string | null
          social_links?: Json | null
          telegram?: string | null
          updated_at?: string
          yandex_metrika_id?: string | null
        }
        Relationships: []
      }
      user_roles: {
        Row: {
          created_at: string
          id: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          user_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      get_public_analytics: {
        Args: never
        Returns: {
          analytics_enabled: boolean
          google_analytics_id: string
          yandex_metrika_id: string
        }[]
      }
      get_public_site_settings: {
        Args: never
        Returns: {
          bot_link: string
          bot_widget_enabled: boolean
          bot_widget_text: string
          email: string
          main_cta_text: string
          og_image: string
          phone: string
          site_description: string
          site_title: string
          social_links: Json
          telegram: string
        }[]
      }
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"]
          _user_id: string
        }
        Returns: boolean
      }
    }
    Enums: {
      app_role: "admin" | "user"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      app_role: ["admin", "user"],
    },
  },
} as const

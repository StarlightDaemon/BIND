import { z } from 'zod';

/**
 * Regex Patterns for Starlight Tokens
 */
const HEX_COLOR = /^#[0-9a-fA-F]{3,6}$/;
const CSS_UNIT = /^[0-9.]+(rem|px|%|em)$/;
const TOKEN_REF = /^{.+}$/; // e.g., {blue.60}
const CSS_FUNC = /^[a-z-]+\(.*\)$/; // e.g. linear-gradient(...)

/**
 * Base Token Types
 */
const HexSchema = z.string().regex(HEX_COLOR, { message: "Must be a valid hex color (e.g. #0f62fe)" });
const UnitSchema = z.string().regex(CSS_UNIT, { message: "Must be a valid CSS unit (rem, px, %, em)" });
const ReferenceSchema = z.string().regex(TOKEN_REF, { message: "Must be a token reference format: {path.to.token}" });
const FunctionSchema = z.string().regex(CSS_FUNC, { message: "Must be a valid CSS function" });

// A Generic Token Value can be any of the above, or a fallback string
const GenericValue = z.union([
    HexSchema,
    UnitSchema,
    ReferenceSchema,
    FunctionSchema,
    z.string().min(1)
]);

/**
 * Recursive Token Group Schema
 * Allows for arbitrary nesting of categories (e.g., colors -> blue -> 10)
 */
export const TokenGroupSchema: z.ZodType<any> = z.lazy(() =>
    z.record(z.union([GenericValue, TokenGroupSchema]))
);

/**
 * Tier 1: Primitives (Raw Values Expected)
 * Should largely be Hex or Units, rarely References.
 */
export const PrimitiveSchema = z.object({
    $schema: z.string().optional(),
    description: z.string().optional(),
    tokens: TokenGroupSchema
});

/**
 * Tier 2: Semantic (References Expected)
 * Values should ideally be references to Primitives.
 */
export const SemanticSchema = z.object({
    $schema: z.string().optional(),
    description: z.string().optional(),
    themes: TokenGroupSchema
});

/**
 * Tier 3: Components (Mixed)
 * Can be overrides or references.
 */
export const ComponentSchema = z.object({
    $schema: z.string().optional(),
    description: z.string().optional(),
    components: TokenGroupSchema
});

/**
 * Unified Parser
 */
export const StarlightTokenSchema = z.union([
    PrimitiveSchema,
    SemanticSchema,
    ComponentSchema
]);

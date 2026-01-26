import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

/**
 * Audit Collector v1.0.0 (Full Compliance Edition)
 * Generates a compliance-evidence.json for the Starlight Carbon Architect.
 * Includes Hex Hunter, Font Hunter, Spacing Hunter, Typography Hunter, and Integrity Hashing.
 */

interface AuditEvidence {
    timestamp: string;
    project_metadata: {
        name: string;
        version: string;
    };
    validator_output: string;
    token_usage_summary: {
        total_tokens_identified: number;
        compliance_percentage: number;
    };
    forensic_analysis: {
        hardcoded_hex_count: number;
        detached_tokens_detected: number;
        suspicious_files: string[];
    };
    font_analysis: {
        non_carbon_fonts_count: number;
        forbidden_fonts: string[];
        files_with_font_violations: string[];
    };
    spacing_analysis: {
        invalid_spacing_count: number;
        invalid_spacings: string[];
        files_with_spacing_violations: string[];
    };
    typography_analysis: {
        invalid_typography_count: number;
        invalid_sizes: string[];
        files_with_typography_violations: string[];
    };
    law_integrity: {
        validator_exists: boolean;
        tokens_hash: string;
    };
}

// ------------------------------------------------------------------
// 1. Integrity Hashing
// ------------------------------------------------------------------
function getTokensHash(tokensDir: string): string {
    if (!fs.existsSync(tokensDir)) return 'NOT_FOUND';

    // Sort files to ensure deterministic hash
    const files = fs.readdirSync(tokensDir).filter(f => f.endsWith('.json')).sort();

    const hash = crypto.createHash('sha256');

    files.forEach(file => {
        const content = fs.readFileSync(path.join(tokensDir, file));
        hash.update(content);
    });

    return `SHA256:${hash.digest('hex')}`;
}

// ------------------------------------------------------------------
// 2. Hex Hunter (Drift Detection)
// ------------------------------------------------------------------
interface ScanResult {
    hexCount: number;
    suspiciousFiles: string[];
}

function recursiveScan(dir: string, extensions: string[] = ['.css', '.scss', '.js', '.ts', '.tsx', '.py']): ScanResult {
    let result: ScanResult = { hexCount: 0, suspiciousFiles: [] };
    const baseName = path.basename(dir);

    // Smart Ignore List (Infrastructure & Tools)
    const IGNORE_DIRS = [
        'node_modules',
        'venv', '.venv', 'env',
        'dist', 'build', 'out',
        '.git', '.idea', '.vscode',
        '__pycache__',
        'governance', '.governance', // Don't audit the auditor
        'starlight-governance-kit' // Don't audit the distribution folder
    ];

    // Skip ignored directories and hidden files (starting with .)
    if (baseName.startsWith('.') || IGNORE_DIRS.some(d => baseName.includes(d))) {
        return result;
    }

    try {
        const entries = fs.readdirSync(dir, { withFileTypes: true });

        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);

            if (entry.isDirectory()) {
                const subResult = recursiveScan(fullPath, extensions);
                result.hexCount += subResult.hexCount;
                result.suspiciousFiles.push(...subResult.suspiciousFiles);
            } else if (extensions.includes(path.extname(entry.name))) {
                const content = fs.readFileSync(fullPath, 'utf-8');
                // Regex for Hex Codes (3 or 6 digits)
                const hexRegex = /#(?:[0-9a-fA-F]{3}){1,2}\b/g;
                const matches = content.match(hexRegex);

                if (matches && matches.length > 0) {
                    result.hexCount += matches.length;
                    result.suspiciousFiles.push(fullPath);
                }
            }
        }
    } catch (e) {
        // Ignore access errors
    }

    return result;
}

// ------------------------------------------------------------------
// 3. Font Hunter (Typography Enforcement)
// ------------------------------------------------------------------
interface FontScanResult {
    violationCount: number;
    forbiddenFonts: string[];
    filesWithViolations: string[];
}

const ALLOWED_FONTS = [
    'ibm plex sans',
    'ibm plex mono',
    'ibm plex serif',
    'helvetica neue',
    'arial',
    'sans-serif',
    'serif',
    'monospace',
    'inherit',
    'var(--font-sans)',
    'var(--font-mono)'
];

function scanForFonts(dir: string, extensions: string[] = ['.css', '.scss', '.html']): FontScanResult {
    let result: FontScanResult = { violationCount: 0, forbiddenFonts: [], filesWithViolations: [] };
    const baseName = path.basename(dir);

    // Smart Ignore List
    const IGNORE_DIRS = [
        'node_modules', 'venv', '.venv', 'env',
        'dist', 'build', 'out',
        '.git', '.idea', '.vscode',
        '__pycache__', 'governance', '.governance',
        'starlight-governance-kit'
    ];

    if (baseName.startsWith('.') || IGNORE_DIRS.some(d => baseName.includes(d))) {
        return result;
    }

    try {
        const entries = fs.readdirSync(dir, { withFileTypes: true });

        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);

            if (entry.isDirectory()) {
                const subResult = scanForFonts(fullPath, extensions);
                result.violationCount += subResult.violationCount;
                result.forbiddenFonts.push(...subResult.forbiddenFonts);
                result.filesWithViolations.push(...subResult.filesWithViolations);
            } else if (extensions.includes(path.extname(entry.name))) {
                const content = fs.readFileSync(fullPath, 'utf-8');
                // Regex for font-family declarations
                const fontRegex = /font-family\s*:\s*([^;]+);/gi;
                let match;

                while ((match = fontRegex.exec(content)) !== null) {
                    const fontValue = match[1].toLowerCase().trim();
                    // Check if any part of the font stack is NOT in allowed list
                    const fontParts = fontValue.split(',').map(f => f.trim().replace(/['"]/g, ''));

                    for (const font of fontParts) {
                        if (!ALLOWED_FONTS.some(allowed => font.includes(allowed))) {
                            result.violationCount++;
                            if (!result.forbiddenFonts.includes(font)) {
                                result.forbiddenFonts.push(font);
                            }
                            if (!result.filesWithViolations.includes(fullPath)) {
                                result.filesWithViolations.push(fullPath);
                            }
                        }
                    }
                }
            }
        }
    } catch (e) {
        // Ignore access errors
    }

    return result;
}

// ------------------------------------------------------------------
// 4. Spacing Hunter (Layout Enforcement)
// ------------------------------------------------------------------
interface SpacingScanResult {
    violationCount: number;
    invalidSpacings: string[];
    filesWithViolations: string[];
}

// Carbon Design System spacing scale (in px)
const CARBON_SPACING_SCALE = [0, 2, 4, 8, 12, 16, 24, 32, 40, 48];

// Common CSS properties that use spacing
const SPACING_PROPERTIES = [
    'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
    'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
    'gap', 'row-gap', 'column-gap',
    'top', 'right', 'bottom', 'left'
];

function scanForSpacing(dir: string, extensions: string[] = ['.css', '.scss', '.html']): SpacingScanResult {
    let result: SpacingScanResult = { violationCount: 0, invalidSpacings: [], filesWithViolations: [] };
    const baseName = path.basename(dir);

    // Smart Ignore List
    const IGNORE_DIRS = [
        'node_modules', 'venv', '.venv', 'env',
        'dist', 'build', 'out',
        '.git', '.idea', '.vscode',
        '__pycache__', 'governance', '.governance',
        'starlight-governance-kit'
    ];

    if (baseName.startsWith('.') || IGNORE_DIRS.some(d => baseName.includes(d))) {
        return result;
    }

    try {
        const entries = fs.readdirSync(dir, { withFileTypes: true });

        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);

            if (entry.isDirectory()) {
                const subResult = scanForSpacing(fullPath, extensions);
                result.violationCount += subResult.violationCount;
                result.invalidSpacings.push(...subResult.invalidSpacings);
                result.filesWithViolations.push(...subResult.filesWithViolations);
            } else if (extensions.includes(path.extname(entry.name))) {
                const content = fs.readFileSync(fullPath, 'utf-8');

                // Build regex for spacing properties with px values
                for (const prop of SPACING_PROPERTIES) {
                    const regex = new RegExp(`${prop}\\s*:\\s*([^;]+);`, 'gi');
                    let match;

                    while ((match = regex.exec(content)) !== null) {
                        const value = match[1].trim();

                        // Skip var() references and auto/inherit
                        if (value.includes('var(') || value === 'auto' || value === 'inherit' || value === '0') {
                            continue;
                        }

                        // Extract px values from the declaration
                        const pxMatches = value.match(/(\d+(?:\.\d+)?)\s*px/gi);
                        if (pxMatches) {
                            for (const pxMatch of pxMatches) {
                                const pxValue = parseFloat(pxMatch);
                                if (!CARBON_SPACING_SCALE.includes(pxValue)) {
                                    result.violationCount++;
                                    const violation = `${prop}: ${pxValue}px`;
                                    if (!result.invalidSpacings.includes(violation)) {
                                        result.invalidSpacings.push(violation);
                                    }
                                    if (!result.filesWithViolations.includes(fullPath)) {
                                        result.filesWithViolations.push(fullPath);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    } catch (e) {
        // Ignore access errors
    }

    return result;
}

// ------------------------------------------------------------------
// 5. Typography Hunter (Type Scale Enforcement)
// ------------------------------------------------------------------
interface TypographyScanResult {
    violationCount: number;
    invalidSizes: string[];
    filesWithViolations: string[];
}

// Carbon Design System type scale (in px)
const CARBON_TYPE_SCALE = [12, 14, 16, 18, 20, 24, 28, 32, 42, 54, 76];

function scanForTypography(dir: string, extensions: string[] = ['.css', '.scss', '.html']): TypographyScanResult {
    let result: TypographyScanResult = { violationCount: 0, invalidSizes: [], filesWithViolations: [] };
    const baseName = path.basename(dir);

    // Smart Ignore List
    const IGNORE_DIRS = [
        'node_modules', 'venv', '.venv', 'env',
        'dist', 'build', 'out',
        '.git', '.idea', '.vscode',
        '__pycache__', 'governance', '.governance',
        'starlight-governance-kit'
    ];

    if (baseName.startsWith('.') || IGNORE_DIRS.some(d => baseName.includes(d))) {
        return result;
    }

    try {
        const entries = fs.readdirSync(dir, { withFileTypes: true });

        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);

            if (entry.isDirectory()) {
                const subResult = scanForTypography(fullPath, extensions);
                result.violationCount += subResult.violationCount;
                result.invalidSizes.push(...subResult.invalidSizes);
                result.filesWithViolations.push(...subResult.filesWithViolations);
            } else if (extensions.includes(path.extname(entry.name))) {
                const content = fs.readFileSync(fullPath, 'utf-8');

                // Match font-size declarations
                const fontSizeRegex = /font-size\s*:\s*([^;]+);/gi;
                let match;

                while ((match = fontSizeRegex.exec(content)) !== null) {
                    const value = match[1].trim();

                    // Skip var() references and rem/em without px
                    if (value.includes('var(') || value === 'inherit' || value === 'initial') {
                        continue;
                    }

                    // Extract px values
                    const pxMatch = value.match(/(\d+(?:\.\d+)?)\s*px/i);
                    if (pxMatch) {
                        const pxValue = parseFloat(pxMatch[1]);
                        if (!CARBON_TYPE_SCALE.includes(pxValue)) {
                            result.violationCount++;
                            const violation = `${pxValue}px`;
                            if (!result.invalidSizes.includes(violation)) {
                                result.invalidSizes.push(violation);
                            }
                            if (!result.filesWithViolations.includes(fullPath)) {
                                result.filesWithViolations.push(fullPath);
                            }
                        }
                    }

                    // Also check rem values (assuming 16px base)
                    const remMatch = value.match(/(\d+(?:\.\d+)?)\s*rem/i);
                    if (remMatch) {
                        const remValue = parseFloat(remMatch[1]);
                        const pxEquivalent = remValue * 16;
                        if (!CARBON_TYPE_SCALE.includes(pxEquivalent)) {
                            result.violationCount++;
                            const violation = `${remValue}rem (${pxEquivalent}px)`;
                            if (!result.invalidSizes.includes(violation)) {
                                result.invalidSizes.push(violation);
                            }
                            if (!result.filesWithViolations.includes(fullPath)) {
                                result.filesWithViolations.push(fullPath);
                            }
                        }
                    }
                }
            }
        }
    } catch (e) {
        // Ignore access errors
    }

    return result;
}

// ------------------------------------------------------------------
// 6. Configuration & Utilities
// ------------------------------------------------------------------

/**
 * Reads project metadata from the target project's package.json.
 * Falls back to sensible defaults if file is missing or malformed.
 * 
 * @param projectRoot - Absolute path to the project root directory
 * @returns Object containing project name and version
 */
function getProjectMetadata(projectRoot: string): { name: string; version: string } {
    const packageJsonPath = path.join(projectRoot, 'package.json');

    try {
        if (fs.existsSync(packageJsonPath)) {
            const content = fs.readFileSync(packageJsonPath, 'utf-8');
            const parsed = JSON.parse(content);
            return {
                name: parsed.name || path.basename(projectRoot),
                version: parsed.version || '0.0.0'
            };
        }
    } catch (e) {
        // JSON parse error - fall through to defaults
    }

    // Fallback: use directory name as project name
    return {
        name: path.basename(projectRoot),
        version: '0.0.0'
    };
}

/**
 * Writes execution log for audit traceability.
 * Creates timestamped record of each audit run.
 * 
 * @param outputDir - Directory to write the execution log
 * @param audit - The audit evidence object
 */
function writeExecutionLog(outputDir: string, audit: AuditEvidence): void {
    const logPath = path.resolve(outputDir, 'execution_log.json');

    interface ExecutionEntry {
        timestamp: string;
        project: string;
        result: string;
        hex_violations: number;
    }

    let log: ExecutionEntry[] = [];

    // Append to existing log if present
    if (fs.existsSync(logPath)) {
        try {
            log = JSON.parse(fs.readFileSync(logPath, 'utf-8'));
        } catch (e) {
            log = []; // Reset if corrupted
        }
    }

    log.push({
        timestamp: audit.timestamp,
        project: audit.project_metadata.name,
        result: audit.forensic_analysis.hardcoded_hex_count === 0 ? 'CLEAN' : 'VIOLATIONS_FOUND',
        hex_violations: audit.forensic_analysis.hardcoded_hex_count
    });

    fs.writeFileSync(logPath, JSON.stringify(log, null, 2));
}

// ------------------------------------------------------------------
// Main Entry Point
// ------------------------------------------------------------------

/**
 * Audit Collector CLI Entry Point
 * 
 * Usage: npx ts-node audit-collector.ts [--project-root <path>]
 * 
 * If --project-root is not specified, defaults to ../../ (relative to CWD).
 * Outputs compliance-evidence.json and appends to execution_log.json.
 */
function main() {
    console.log("🕵️ Starlight Governance Audit Collector v0.8.0");
    console.log("   Font Enforcement Edition - Hex Hunter + Font Hunter + Integrity Hashing\n");

    // Parse CLI arguments for project root override
    const args = process.argv.slice(2);
    const projectRootArgIndex = args.indexOf('--project-root');

    let projectRoot: string;
    if (projectRootArgIndex !== -1 && args[projectRootArgIndex + 1]) {
        projectRoot = path.resolve(args[projectRootArgIndex + 1]);
    } else {
        // Default: Assuming running from project/.governance/validator or governance kit
        projectRoot = path.resolve(process.cwd(), '../../');
    }

    const tokensDir = path.resolve(process.cwd(), '../tokens');

    console.log(`   Project Root: ${projectRoot}`);
    console.log(`   Tokens Dir:   ${tokensDir}\n`);

    // 1. Read Project Metadata (dynamic, not hardcoded)
    const projectMeta = getProjectMetadata(projectRoot);
    console.log(`   Target: ${projectMeta.name} v${projectMeta.version}`);

    // 2. Integrity Check
    const tokenHash = getTokensHash(tokensDir);
    console.log(`   Token Hash: ${tokenHash.substring(0, 20)}...`);

    // 3. Forensic Scan (Hex Hunter)
    console.log("   Initializing Hex Hunter...");
    const hexResult = recursiveScan(projectRoot);
    console.log(`   Found ${hexResult.hexCount} hardcoded hex values in ${hexResult.suspiciousFiles.length} files.`);

    // 4. Font Scan (Font Hunter)
    console.log("   Initializing Font Hunter...");
    const fontResult = scanForFonts(projectRoot);
    console.log(`   Found ${fontResult.violationCount} non-Carbon fonts in ${fontResult.filesWithViolations.length} files.`);

    // 5. Spacing Scan (Spacing Hunter)
    console.log("   Initializing Spacing Hunter...");
    const spacingResult = scanForSpacing(projectRoot);
    console.log(`   Found ${spacingResult.violationCount} non-Carbon spacings in ${spacingResult.filesWithViolations.length} files.`);

    // 6. Typography Scan (Typography Hunter)
    console.log("   Initializing Typography Hunter...");
    const typographyResult = scanForTypography(projectRoot);
    console.log(`   Found ${typographyResult.violationCount} non-Carbon font sizes in ${typographyResult.filesWithViolations.length} files.`);

    // 7. Calculate compliance percentage (based on all violations)
    const totalViolations = hexResult.hexCount + fontResult.violationCount + spacingResult.violationCount + typographyResult.violationCount;
    const complianceScore = totalViolations === 0
        ? 100
        : Math.max(0, 100 - (totalViolations * 2)); // -2% per violation

    const audit: AuditEvidence = {
        timestamp: new Date().toISOString(),
        project_metadata: projectMeta,
        validator_output: fs.existsSync(path.resolve(process.cwd(), 'validate-tokens.ts'))
            ? "Validator available - run 'npm run validate' for full check"
            : "Validator not found in current directory",
        token_usage_summary: {
            total_tokens_identified: hexResult.hexCount,
            compliance_percentage: complianceScore
        },
        forensic_analysis: {
            hardcoded_hex_count: hexResult.hexCount,
            detached_tokens_detected: hexResult.hexCount,
            suspicious_files: hexResult.suspiciousFiles.slice(0, 10)
        },
        font_analysis: {
            non_carbon_fonts_count: fontResult.violationCount,
            forbidden_fonts: fontResult.forbiddenFonts.slice(0, 10),
            files_with_font_violations: fontResult.filesWithViolations.slice(0, 10)
        },
        spacing_analysis: {
            invalid_spacing_count: spacingResult.violationCount,
            invalid_spacings: spacingResult.invalidSpacings.slice(0, 10),
            files_with_spacing_violations: spacingResult.filesWithViolations.slice(0, 10)
        },
        typography_analysis: {
            invalid_typography_count: typographyResult.violationCount,
            invalid_sizes: typographyResult.invalidSizes.slice(0, 10),
            files_with_typography_violations: typographyResult.filesWithViolations.slice(0, 10)
        },
        law_integrity: {
            validator_exists: fs.existsSync(path.resolve(process.cwd(), 'validate-tokens.ts')),
            tokens_hash: tokenHash
        }
    };

    // 8. Write outputs
    const outputPath = path.resolve(process.cwd(), 'compliance-evidence.json');
    fs.writeFileSync(outputPath, JSON.stringify(audit, null, 4));

    // 9. Write execution log for audit trail
    writeExecutionLog(process.cwd(), audit);

    console.log(`\n✅ Evidence collected at: ${outputPath}`);
    console.log(`📋 Execution logged to: execution_log.json`);
    console.log(`\n📊 Compliance Score: ${complianceScore}%`);

    if (hexResult.hexCount > 0) {
        console.log(`\n⚠️  ${hexResult.hexCount} hardcoded hex values detected.`);
    }
    if (fontResult.violationCount > 0) {
        console.log(`\n🔤 ${fontResult.violationCount} non-Carbon font(s) detected: ${fontResult.forbiddenFonts.join(', ')}`);
    }
    if (spacingResult.violationCount > 0) {
        console.log(`\n📏 ${spacingResult.violationCount} non-Carbon spacing(s) detected: ${spacingResult.invalidSpacings.slice(0, 5).join(', ')}`);
    }
    if (typographyResult.violationCount > 0) {
        console.log(`\n🔠 ${typographyResult.violationCount} non-Carbon font size(s) detected: ${typographyResult.invalidSizes.slice(0, 5).join(', ')}`);
    }
    if (totalViolations === 0) {
        console.log(`\n🎉 Perfect compliance! No violations found.`);
    }
}

main();


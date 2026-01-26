import * as fs from 'fs';
import * as path from 'path';
import chalk from 'chalk';
import { PrimitiveSchema, SemanticSchema, ComponentSchema } from './src/rules';

const PROD_TOKENS = path.resolve(process.cwd(), '../tokens'); // Exported Kit structure
const DEV_TOKENS = path.resolve(process.cwd(), '../../.governance/tokens'); // Local Source structure

const TOKENS_DIR = fs.existsSync(PROD_TOKENS) ? PROD_TOKENS : DEV_TOKENS;

function validateFile(filePath: string): { valid: boolean; errors: string[] } {
    const fileName = path.basename(filePath);
    let schema;

    if (fileName.includes('primitives')) {
        schema = PrimitiveSchema;
    } else if (fileName.includes('semantic')) {
        schema = SemanticSchema;
    } else if (fileName.includes('component')) {
        schema = ComponentSchema;
    } else {
        return { valid: false, errors: [`Unknown token file type: ${fileName}`] };
    }

    try {
        const content = fs.readFileSync(filePath, 'utf-8');
        const json = JSON.parse(content);

        const result = schema.safeParse(json);

        if (!result.success) {
            // Format Zod errors
            const errors = result.error.errors.map(e => {
                const pathStr = e.path.join('.');
                return `${chalk.bold(pathStr)}: ${e.message}`;
            });
            return { valid: false, errors };
        }

        return { valid: true, errors: [] };

    } catch (e: any) {
        return { valid: false, errors: [`JSON Parse/Read Error: ${e.message}`] };
    }
}

function main() {
    console.log(chalk.blue.bold(`\n🔍 Starlight Governance Validator`));
    console.log(chalk.dim(`Checking directory: ${TOKENS_DIR}\n`));

    if (!fs.existsSync(TOKENS_DIR)) {
        console.error(chalk.red(`❌ Tokens directory not found: ${TOKENS_DIR}`));
        process.exit(1);
    }

    const files = fs.readdirSync(TOKENS_DIR).filter(f => f.endsWith('.json'));
    let hasErrors = false;

    console.log(chalk.underline('Results:'));

    for (const file of files) {
        const fullPath = path.join(TOKENS_DIR, file);
        const { valid, errors } = validateFile(fullPath);

        if (valid) {
            console.log(`${chalk.green('✔ PASS')}  ${file}`);
        } else {
            hasErrors = true;
            console.log(`${chalk.red('✖ FAIL')}  ${file}`);
            errors.forEach(err => console.log(chalk.yellow(`   ↳ ${err}`)));
        }
    }

    console.log('\n' + '-'.repeat(40) + '\n');

    if (hasErrors) {
        console.log(chalk.red.bold('🚨 Validation Failed. Governance constraints violated.'));
        process.exit(1);
    } else {
        console.log(chalk.green.bold('✨ All Systems Nominal. Governance validation passed.'));
        process.exit(0);
    }
}

main();

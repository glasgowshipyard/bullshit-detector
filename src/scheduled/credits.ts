/**
 * Credit status update scheduled task
 * Checks DeepSeek API balance
 */

import type { Env } from '../models/types';

interface CreditStatus {
  last_updated: string;
  balance: number;
  currency: string;
}

/**
 * Update credit status from DeepSeek API
 */
export async function updateCreditStatus(env: Env): Promise<void> {
  console.log('Updating credit status...');

  try {
    const response = await fetch('https://api.deepseek.com/user/balance', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${env.DEEPSEEK_API_KEY}`,
      },
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      console.error(`Error fetching credit status: HTTP ${response.status}`);
      return;
    }

    const data = (await response.json()) as any;

    const status: CreditStatus = {
      last_updated: new Date().toISOString(),
      balance: data.balance_infos?.[0]?.total_balance || 0,
      currency: data.balance_infos?.[0]?.currency || 'USD',
    };

    // Save to Workers KV
    await env.CACHE.put('credit_status', JSON.stringify(status));
    console.log(`Credit status updated: ${status.balance} ${status.currency}`);
  } catch (error: any) {
    console.error(`Failed to update credit status: ${error.message}`);
  }
}

/**
 * /create-checkout-session endpoint handler
 * Creates Stripe checkout sessions for donations
 */

import type { Env } from '../models/types';
import Stripe from 'stripe';

export async function handleCheckout(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const body = (await request.json()) as any;
    const amount = body.amount || 500; // Default $5.00 in cents

    if (amount < 100 || amount > 1000) {
      return new Response(JSON.stringify({ error: 'Amount must be between $1 and $10' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const stripe = new Stripe(env.STRIPE_SECRET_KEY, {
      apiVersion: '2025-12-15.clover' as any,
    });

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      line_items: [
        {
          price_data: {
            currency: 'usd',
            product_data: {
              name: 'Bullshit Detector Donation',
              description: 'Support ongoing AI API costs',
            },
            unit_amount: amount, // Already in cents from frontend
          },
          quantity: 1,
        },
      ],
      mode: 'payment',
      success_url: 'https://bullshitdetector.ai/success',
      cancel_url: 'https://bullshitdetector.ai',
    });

    return new Response(JSON.stringify({ id: session.id }), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error: any) {
    console.error('Error in /create-checkout-session route:', error);
    return new Response(
      JSON.stringify({
        error: 'Internal server error',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

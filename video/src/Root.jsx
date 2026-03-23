import React from 'react';
import {Composition} from 'remotion';
import {DVRRShowcaseTerminal, SHOWCASE_TOTAL_FRAMES} from './ShowcaseTerminal.jsx';

const defaultProps = {
  symbol: 'GOOG',
  accountEquity: 2151.71,
  positionCount: 9,
  regimeTrend: 'DOWNTREND',
  regimeVolatility: 'MEDIUM',
  trendConfidence: 0.8,
  tradability: 0.5,
  sleeveTrend: 0.55,
  sleeveBreakout: 0.3,
  sleeveReversion: 0.15,
  price: 298.79,
  sma50: 318.04,
  sma200: 260.47,
  rsi: 39.5,
  macdHist: 0.4093,
  trendScore: 0.0256,
  momentum3m: -6.09,
  momentum6m: 25.2,
  verdict: 'HOLD',
};

export const RemotionRoot = () => {
  return (
    <Composition
      id="DVRRShowcase"
      component={DVRRShowcaseTerminal}
      durationInFrames={SHOWCASE_TOTAL_FRAMES}
      fps={30}
      width={1280}
      height={720}
      defaultProps={defaultProps}
    />
  );
};

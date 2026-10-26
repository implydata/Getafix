package io.imply;

import org.apache.druid.query.BaseQuery;

import java.util.Date;

public class LogEntry
{
  public final String  type ;
  public final BaseQuery  query ;
  public final Date eventTime ;

  public final long executionTime ;
  public LogEntry(Date eventTime, String type, BaseQuery query , long  executionTime) {
    this.type = type;
    this.query = query;
    this.eventTime = eventTime;
    this.executionTime = executionTime;
  }
}

<%@ page contentType="text/xml; charset=UTF-8" pageEncoding="UTF-8" trimDirectiveWhitespaces="true" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c"%>
<?xml version="1.0" encoding="UTF-8"?>
<Root xmlns="http://www.tobesoft.com/platform/dataset" ver="5000">
	<Parameters>
		<Parameter id="ErrorCode" type="int">${data.code}</Parameter>
		<Parameter id="ErrorMsg" type="string"><c:out value="${data.message}"/></Parameter>
	</Parameters>
	<c:forEach items="${data.datasets}" var ="dataset">
        <Dataset id="${dataset.id}">
            <ColumnInfo>
                <c:forEach items="${dataset.columns}" var="column">
                    <Column id="${column.id}" type="${column.type}" size="${column.size}"/>
                </c:forEach>
            </ColumnInfo>
            <Rows>
              <c:forEach items="${dataset.rows}" var="row">
                <Row>
                    <c:forEach items="${row}" var="r">
                        <Col id="${r.key}"><c:out value="${r.value}"/></Col>
                    </c:forEach>
                </Row>
              </c:forEach>
            </Rows>
        </Dataset>
	</c:forEach>
</Root>
